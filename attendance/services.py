from zk import ZK
from django.db.models import Max
from django.utils import timezone
from .models import Employee, AttendanceLog, DailySummary
import logging
import time

logger = logging.getLogger(__name__)

class BiometricService:
    def sync_device(self, ip=None, port=None, max_retries=3):
        """
        Sync with ZK biometric device with retry logic
        
        Args:
            ip: Device IP address (optional, uses DeviceSettings if not provided)
            port: Device port (optional, uses DeviceSettings if not provided)
            max_retries: Maximum number of retry attempts
        """
        from .models import DeviceSettings
        
        # Get device settings from database
        device_settings = DeviceSettings.get_settings()
        
        # Use provided values or fall back to database settings
        ip = ip or device_settings.device_ip
        port = port or device_settings.device_port
        timeout = device_settings.timeout
        password = device_settings.password
        force_udp = device_settings.force_udp
        ommit_ping = device_settings.ommit_ping
        
        for attempt in range(max_retries):
            zk = ZK(ip, port=port, timeout=timeout, password=password, 
                   force_udp=force_udp, ommit_ping=ommit_ping)
            conn = None
            
            try:
                logger.info(f"Connecting to device at {ip}:{port}... (Attempt {attempt + 1}/{max_retries})")
                conn = zk.connect()
                
                # Disable device to prevent interference during sync
                logger.info("Disabling device for sync...")
                conn.disable_device()
                
                # Small delay to ensure device is ready
                time.sleep(0.5)
                
                # 1. Sync Users
                logger.info("Fetching users...")
                zk_users = conn.get_users()
                logger.info(f"Found {len(zk_users)} users")
                self._sync_users(zk_users)
                
                # 2. Sync Attendance
                logger.info("Fetching attendance logs...")
                attendance_records = conn.get_attendance()
                logger.info(f"Downloaded {len(attendance_records)} attendance records")
                
                self._sync_attendance(attendance_records)
                
                logger.info("✓ Sync completed successfully")
                return  # Success - exit the retry loop
                
            except ConnectionError as e:
                logger.error(f"Connection error on attempt {attempt + 1}: {e}")
                if attempt < max_retries - 1:
                    logger.info(f"Retrying in 2 seconds...")
                    time.sleep(2)
                else:
                    logger.error(f"Failed after {max_retries} attempts")
                    raise e
                    
            except BrokenPipeError as e:
                logger.error(f"Broken pipe error on attempt {attempt + 1}: {e}")
                if attempt < max_retries - 1:
                    logger.info(f"Retrying in 3 seconds...")
                    time.sleep(3)
                else:
                    logger.error(f"Failed after {max_retries} attempts")
                    raise e
                    
            except Exception as e:
                logger.error(f"Error during sync (attempt {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    logger.info(f"Retrying in 2 seconds...")
                    time.sleep(2)
                else:
                    logger.error(f"Failed after {max_retries} attempts")
                    raise e
                    
            finally:
                # Always try to re-enable device and disconnect
                if conn:
                    try:
                        logger.info("Re-enabling device...")
                        conn.enable_device()
                        time.sleep(0.3)
                        logger.info("Disconnecting...")
                        conn.disconnect()
                    except Exception as cleanup_error:
                        logger.warning(f"Error during cleanup: {cleanup_error}")

    def _sync_users(self, zk_users):
        for user in zk_users:
            # user.user_id is the string ID (Badge ID)
            # user.uid is the internal integer ID
            # Update or create employee
            Employee.objects.update_or_create(
                biometric_id=user.uid,
                defaults={
                    'name': user.name,
                    'employee_id': user.user_id
                }
            )

    def _sync_attendance(self, records):
        if not records:
            return

        # Pre-fetch employees for FK mapping: Map employee_id (str) -> Employee Object
        employee_map = {e.employee_id: e for e in Employee.objects.all()}
        current_tz = timezone.get_current_timezone()
        
        # 1. Process records into a standardized list of dicts
        processed_records = []
        timestamps = []
        
        # Track all potential (employee_id, date) pairs that might need summaries
        all_record_dates = set()

        for rec in records:
            rec_time = rec.timestamp
            # Ensure timezone awareness
            if timezone.is_aware(rec_time) is False:
                rec_time = timezone.make_aware(rec_time, current_tz)
            
            # Find employee using the string ID (Badge ID)
            employee = employee_map.get(str(rec.user_id))
            if not employee:
                continue
            
            processed_records.append({
                'employee': employee,
                'timestamp': rec_time,
                'status': rec.status,
                'verification_mode': rec.punch if hasattr(rec, 'punch') else 0
            })
            timestamps.append(rec_time)
            all_record_dates.add((employee.id, rec_time.date()))

        if not processed_records:
            logger.info("No valid records found to process.")
            return

        # Log the range we received for debugging
        if timestamps:
            min_ts = min(timestamps)
            max_ts = max(timestamps)
            logger.info(f"Processing batch from {min_ts} to {max_ts}")

            # 2. Optimization: Identify existing LOGS to avoid duplicates
            existing_logs = set(
                AttendanceLog.objects.filter(
                    timestamp__range=(min_ts, max_ts)
                ).values_list('employee_id', 'timestamp')
            )
        else:
            existing_logs = set()

        # 3. Create list of new AttendanceLog objects
        new_logs = []
        batch_signatures = set()

        for item in processed_records:
            signature = (item['employee'].id, item['timestamp'])
            
            # unique_together check
            if signature not in existing_logs and signature not in batch_signatures:
                new_logs.append(AttendanceLog(
                    employee=item['employee'],
                    timestamp=item['timestamp'],
                    status=item['status'],
                    verification_mode=item['verification_mode']
                ))
                batch_signatures.add(signature)

        # 4. Bulk Insert Logs
        if new_logs:
            AttendanceLog.objects.bulk_create(new_logs)
            logger.info(f"Inserted {len(new_logs)} new attendance logs.")
        else:
            logger.info("All logs already exist.")

        # 5. Update Summaries
        # Logic:
        # We need to update summaries for:
        # A) Any dates where we just added new logs (new_logs)
        # B) Any dates present in the payload but MISSING from DailySummary table (backfill)
        
        # Set A: Dates from new logs
        dates_to_update = set()
        for log in new_logs:
            dates_to_update.add((log.employee.id, log.timestamp.date()))
        
        # Set B: Check for missing summaries within the range of data we fetched
        # Only check if we have potential dates to check
        if all_record_dates:
            # We can efficiently find which of all_record_dates exist in DailySummary
            # But fetching ALL summaries for the range might be heavy if range is huge (years).
            # However, usually we care about the specific (emp, date) pairs.
            # Building a query for specific pairs is hard in Django ORM without huge Q objects.
            # Instead, let's query the DailySummary for the min/max date range and filter in memory.
            
            min_date = min(d for _, d in all_record_dates)
            max_date = max(d for _, d in all_record_dates)
            
            existing_summaries = set(
                DailySummary.objects.filter(
                    date__range=(min_date, max_date)
                ).values_list('employee_id', 'date')
            )
            
            # Find which ones from our batch are missing
            missing_summaries = all_record_dates - existing_summaries
            if missing_summaries:
                logger.info(f"Found {len(missing_summaries)} missing summaries. Scheduling update.")
                dates_to_update.update(missing_summaries)

        if dates_to_update:
            self._update_summaries(list(dates_to_update))
        else:
            logger.info("No summaries needed update.")

    def _update_summaries(self, affected_keys):
        from .models import WorkSettings, Shift
        from .shift_utils import detect_shift_for_attendance, calculate_night_hours, calculate_break_overlap
        from datetime import datetime, timedelta
        
        settings = WorkSettings.get_settings()
        
        # Group affected keys by employee to process all dates together
        employee_dates = {}
        for emp_id, log_date in affected_keys:
            if emp_id not in employee_dates:
                employee_dates[emp_id] = set()
            employee_dates[emp_id].add(log_date)
        
        for emp_id, dates in employee_dates.items():
            employee = Employee.objects.get(id=emp_id)
            
            # Expand date range to catch night shifts
            min_date = min(dates) - timedelta(days=1)
            max_date = max(dates) + timedelta(days=1)
            
            # Get all logs in the expanded range
            all_logs = AttendanceLog.objects.filter(
                employee_id=emp_id,
                timestamp__date__gte=min_date,
                timestamp__date__lte=max_date
            ).order_by('timestamp')
            
            if not all_logs.exists():
                continue
            
            # Group logs by detected shift
            shift_groups = self._group_logs_by_shift(employee, all_logs)
            
            # Process each shift group
            for (shift, shift_date), logs in shift_groups.items():
                if not logs or len(logs) < 1:
                    continue
                
                first_in = logs[0].timestamp
                last_out = logs[-1].timestamp
                
                # Calculate raw working hours
                if len(logs) > 1:
                    total_seconds = (last_out - first_in).total_seconds()
                    total_time = total_seconds / 3600.0
                else:
                    total_time = 0.0
                
                # Calculate night vs day hours
                night_hours, day_hours = calculate_night_hours(
                    first_in,
                    last_out,
                    settings.night_start_time,
                    settings.night_end_time
                )
                
                # Subtract break time
                break_hours = 0.0
                if shift and shift.exclude_break and shift.break_start_time and shift.break_end_time:
                    # Use shift-specific break
                    break_hours = calculate_break_overlap(
                        first_in,
                        last_out,
                        shift.break_start_time,
                        shift.break_end_time
                    )
                elif settings.exclude_lunch_from_hours:
                    # Use global lunch break
                    break_hours = calculate_break_overlap(
                        first_in,
                        last_out,
                        settings.lunch_start_time,
                        settings.lunch_end_time
                    )
                
                if break_hours > 0:
                    total_time -= break_hours
                    # Proportionally reduce night/day hours
                    if total_time + break_hours > 0:
                        ratio = total_time / (total_time + break_hours)
                        night_hours *= ratio
                        day_hours *= ratio
                    logger.debug(f"Excluded {break_hours:.2f}h break for {employee.name} on {shift_date}")
                
                # Get expected working hours
                if shift:
                    expected_hours = float(shift.working_hours)
                else:
                    expected_hours = employee.get_working_hours()
                
                # Calculate overtime
                overtime = max(0.0, total_time - expected_hours)
                is_overtime = overtime > 0
                
                # Calculate night shift allowance
                night_allowance_amount = 0.0
                if shift and shift.night_shift_allowance > 0 and night_hours > 0:
                    # Allowance is percentage of night hours
                    night_allowance_amount = (night_hours * float(shift.night_shift_allowance)) / 100.0
                
                # Update or create summary
                DailySummary.objects.update_or_create(
                    employee_id=emp_id,
                    date=shift_date,
                    shift=shift,
                    defaults={
                        'first_check_in': first_in.time(),
                        'last_check_out': last_out.time(),  # Always set last checkout
                        'total_hours': round(total_time, 2),
                        'night_hours': round(night_hours, 2),
                        'day_hours': round(day_hours, 2),
                        'overtime_hours': round(overtime, 2),
                        'is_overtime': is_overtime,
                        'night_shift_allowance_amount': round(night_allowance_amount, 2)
                    }
                )
                
                logger.info(
                    f"Updated summary for {employee.name} on {shift_date}: "
                    f"{total_time:.2f}h total ({night_hours:.2f}h night, {day_hours:.2f}h day), "
                    f"{overtime:.2f}h OT, Shift: {shift.name if shift else 'None'}"
                )
    
    
    def _group_logs_by_shift(self, employee, logs):
        """
        Group attendance logs by detected shift and work session
        
        For extended shifts that cross midnight, we need to ensure all logs
        from a single work session (check-in to check-out) are grouped together
        using the check-in time to determine the shift date.
        
        Returns:
            dict: {(shift, shift_date): [logs]}
        """
        from .shift_utils import detect_shift_for_attendance
        
        if not logs:
            return {}
        
        shift_groups = {}
        
        # Group logs into work sessions (pairs of check-in/check-out)
        # A work session starts with a check-in and includes all subsequent logs
        # until we see another check-in (which starts a new session)
        
        work_sessions = []
        current_session = []
        
        for log in logs:
            if not current_session:
                # Start new session
                current_session = [log]
            else:
                # Add to current session
                current_session.append(log)
                
                # Check if this might be the end of a session
                # If we have at least 2 logs and the time gap to next log is > 4 hours,
                # or if this is the last log, close the session
                log_index = list(logs).index(log)
                if log_index < len(logs) - 1:
                    next_log = logs[log_index + 1]
                    time_gap = (next_log.timestamp - log.timestamp).total_seconds() / 3600.0
                    if time_gap > 4.0:  # More than 4 hours gap = new session
                        work_sessions.append(current_session)
                        current_session = []
                else:
                    # Last log - close current session
                    work_sessions.append(current_session)
        
        # If there's an unclosed session, add it
        if current_session:
            work_sessions.append(current_session)
        
        # Now group each work session by shift using the FIRST log's timestamp
        for session in work_sessions:
            if not session:
                continue
            
            # Use first log (check-in) to determine shift and date
            first_log = session[0]
            shift, shift_date = detect_shift_for_attendance(employee, first_log.timestamp)
            
            key = (shift, shift_date)
            if key not in shift_groups:
                shift_groups[key] = []
            
            # Add ALL logs from this session to the same shift group
            shift_groups[key].extend(session)
        
        return shift_groups


