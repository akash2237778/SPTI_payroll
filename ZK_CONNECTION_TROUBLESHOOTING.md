# 🔍 ZK Device Connection Troubleshooting

## Issue
Consumer can't reach biometric device even with macvlan network configured.

---

## Quick Diagnostics

### 1. Test from TrueNAS Host

```bash
# SSH to TrueNAS
ssh root@<truenas-ip>

# Test ping
ping -c 4 192.168.2.66

# Test port (should connect)
telnet 192.168.2.66 4370
# Or
nc -zv 192.168.2.66 4370
```

**Expected**: Connection successful

### 2. Test from Consumer Container

```bash
# Get shell in consumer
docker exec -it spti_consumer bash

# Test network connectivity
ping -c 4 192.168.2.66

# Test port (install telnet first if needed)
apt-get update && apt-get install -y telnet
telnet 192.168.2.66 4370
```

**Expected**: Connection successful

### 3. Check Consumer IP

```bash
docker exec spti_consumer ip addr show
```

**Expected**: Should show macvlan IP (192.168.2.200)

---

## Protocol Testing

The ZK device might require specific protocol settings. Run the test script:

```bash
# Copy test script to TrueNAS
scp test_zk_connection.py root@<truenas-ip>:/tmp/

# SSH to TrueNAS
ssh root@<truenas-ip>

# Run from consumer container
docker cp /tmp/test_zk_connection.py spti_consumer:/tmp/
docker exec spti_consumer python /tmp/test_zk_connection.py
```

This will test:
- ✅ TCP vs UDP
- ✅ With/without ping
- ✅ Different timeouts

---

## Common Issues & Fixes

### Issue 1: "Can't reach device (ping)"

**Cause**: Network isolation or ping disabled

**Fix**: Already applied - `ommit_ping=True`

### Issue 2: "Connection timeout"

**Cause**: Wrong protocol (TCP vs UDP)

**Fix**: Changed to UDP
```python
force_udp=True  # Changed from False
```

### Issue 3: "Connection refused"

**Cause**: 
- Device not on network
- Wrong IP address
- Firewall blocking

**Fix**: 
```bash
# Verify device IP
ping 192.168.2.66

# Check if device web interface works
curl http://192.168.2.66

# Try different port
telnet 192.168.2.66 80
```

### Issue 4: Macvlan not working

**Symptoms**: Container can't reach ANY device on LAN

**Fix**: Check macvlan configuration

```bash
# Verify network interface exists
ip link show enp0s31f6

# Check if interface is up
ip link set enp0s31f6 up

# Verify subnet and gateway
ip route
```

### Issue 5: IP conflict

**Symptoms**: Intermittent connectivity

**Fix**: Choose different IP for consumer
```yaml
ipv4_address: 192.168.2.201  # Change from .200
ip_range: 192.168.2.201/32
```

---

## Protocol Comparison

| Protocol | Pros | Cons | When to Use |
|----------|------|------|-------------|
| **TCP** | Reliable, ordered | Slower | Stable networks |
| **UDP** | Fast, less overhead | No guarantee | ZK devices (preferred) |

**Most ZK devices work better with UDP!**

---

## Working Configuration (Updated)

```python
# In attendance/services.py
zk = ZK(
    ip,
    port=port,
    timeout=60,        # Long timeout for slow networks
    password=0,        # No password
    force_udp=True,    # ✅ USE UDP (changed from False)
    ommit_ping=True    # ✅ Skip ping check
)
```

---

## Network Verification Checklist

- [ ] TrueNAS can ping device (192.168.2.66)
- [ ] TrueNAS can connect to port 4370
- [ ] Consumer has macvlan IP (192.168.2.200)
- [ ] Consumer can ping device
- [ ] Consumer can connect to port 4370
- [ ] No IP conflicts on network
- [ ] Firewall allows traffic
- [ ] Device is powered on and connected

---

## Alternative: Test Without Docker

If still failing, test the connection directly on TrueNAS host:

```bash
# Install python-zk on TrueNAS
pip install pyzk

# Create test script
cat > /tmp/test.py << 'EOF'
from zk import ZK

zk = ZK('192.168.2.66', port=4370, timeout=60, password=0, force_udp=True, ommit_ping=True)
conn = zk.connect()
print(f"✅ Connected!")
print(f"Firmware: {conn.get_firmware_version()}")
users = conn.get_users()
print(f"Users: {len(users)}")
conn.disconnect()
EOF

# Run test
python /tmp/test.py
```

If this works, the issue is Docker networking. If it fails, the issue is with the device or network.

---

## Device-Side Checks

### Check Device Settings

1. **Access device web interface**: `http://192.168.2.66`
2. **Verify network settings**:
   - IP: 192.168.2.66
   - Subnet: 255.255.255.0
   - Gateway: 192.168.2.55 (or .1)
3. **Check communication settings**:
   - Protocol: TCP/IP
   - Port: 4370
   - Firewall: Disabled or allow port 4370

### Reset Device Network (if needed)

Some ZK devices have a reset button or menu option to reset network settings to DHCP.

---

## Next Steps

1. **Run test script** to find working protocol
2. **Update services.py** with working parameters
3. **Rebuild Docker image** with new settings
4. **Push to Docker Hub**
5. **Redeploy on TrueNAS**

---

## Current Changes Applied

✅ Changed `force_udp=False` → `force_udp=True`  
✅ Kept `ommit_ping=True`  
✅ Timeout set to 60 seconds  
✅ Macvlan network configured  

**Next**: Test and verify connection works!
