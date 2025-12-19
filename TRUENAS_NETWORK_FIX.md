# 🔧 TrueNAS Network Fix - Macvlan Setup

## Problem
Consumer container can't reach biometric device (192.168.2.66) even with `network_mode: host` because TrueNAS runs Docker in a VM.

## Solution
Use **macvlan network** to give the consumer container its own IP address on your LAN.

---

## Step 1: Find Your Network Interface

SSH to TrueNAS and run:

```bash
ip addr show
```

Look for your main network interface. Common names:
- `eno1`
- `enp0s3`
- `br0`
- `eth0`

Example output:
```
2: eno1: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500
    inet 192.168.2.100/24 brd 192.168.2.255 scope global eno1
```

In this example, the interface is **`eno1`** and the network is **`192.168.2.0/24`**.

---

## Step 2: Choose an Unused IP

Pick an IP address on your network that is:
- ✅ In the same subnet (e.g., 192.168.2.x)
- ✅ NOT used by any other device
- ✅ Outside your DHCP range (check your router settings)

Example: If your DHCP range is `192.168.2.100-192.168.2.199`, use `192.168.2.200`

---

## Step 3: Update docker-compose.yml

Edit the macvlan network section:

```yaml
networks:
  macvlan_network:
    driver: macvlan
    driver_opts:
      parent: eno1                    # ← CHANGE to your interface
    ipam:
      config:
        - subnet: 192.168.2.0/24      # ← CHANGE to your subnet
          gateway: 192.168.2.1         # ← CHANGE to your router IP
          ip_range: 192.168.2.200/32   # ← CHANGE to your chosen IP
```

And update the consumer service:

```yaml
consumer:
  networks:
    spti_network:
    macvlan_network:
      ipv4_address: 192.168.2.200     # ← CHANGE to match ip_range above
```

---

## Step 4: Deploy

### Using Dockge:

1. Copy the updated `docker-compose.truenas-macvlan.yml`
2. Update the network settings (interface, subnet, IP)
3. Paste into Dockge
4. Deploy

### Using CLI:

```bash
cd /mnt/tank/apps/spti-payroll
docker-compose down
docker-compose up -d
```

---

## Step 5: Verify

### Check Consumer IP:

```bash
docker exec spti_consumer ip addr show
```

You should see the macvlan IP (e.g., 192.168.2.200)

### Test Connectivity:

```bash
# From TrueNAS host
ping 192.168.2.66

# From consumer container
docker exec spti_consumer ping -c 2 192.168.2.66
```

### Check Consumer Logs:

```bash
docker logs spti_consumer --tail 50
```

Expected:
```
Connecting to device at 192.168.2.66... (Attempt 1/3)
✓ Sync completed successfully
```

---

## Configuration Examples

### Example 1: Network 192.168.1.x

```yaml
networks:
  macvlan_network:
    driver: macvlan
    driver_opts:
      parent: eno1
    ipam:
      config:
        - subnet: 192.168.1.0/24
          gateway: 192.168.1.1
          ip_range: 192.168.1.200/32

consumer:
  networks:
    macvlan_network:
      ipv4_address: 192.168.1.200
```

### Example 2: Network 10.0.0.x

```yaml
networks:
  macvlan_network:
    driver: macvlan
    driver_opts:
      parent: br0
    ipam:
      config:
        - subnet: 10.0.0.0/24
          gateway: 10.0.0.1
          ip_range: 10.0.0.200/32

consumer:
  networks:
    macvlan_network:
      ipv4_address: 10.0.0.200
```

---

## Troubleshooting

### Issue 1: "network not found"

**Solution**: Create network manually first:

```bash
docker network create -d macvlan \
  --subnet=192.168.2.0/24 \
  --gateway=192.168.2.1 \
  --ip-range=192.168.2.200/32 \
  -o parent=eno1 \
  macvlan_network
```

### Issue 2: "address already in use"

**Solution**: Choose a different IP address that's not in use

### Issue 3: Can't ping consumer from TrueNAS host

**This is normal!** Macvlan prevents host-to-container communication. But the consumer CAN reach:
- ✅ Other devices on LAN (including biometric device)
- ✅ Other Docker containers (via spti_network)

### Issue 4: Consumer still can't reach device

**Check**:
1. Is the device IP correct? (192.168.2.66)
2. Is the device powered on?
3. Is the device on the same network?
4. Can you ping device from TrueNAS host?

```bash
# From TrueNAS
ping 192.168.2.66
telnet 192.168.2.66 4370
```

---

## Why Macvlan?

| Network Mode | Can Access LAN Devices? | Can Access Docker Services? |
|--------------|-------------------------|----------------------------|
| `bridge` | ❌ No | ✅ Yes |
| `host` | ⚠️ Only VM network | ❌ No |
| `macvlan` | ✅ Yes | ✅ Yes (with dual network) |

**Macvlan** gives the container its own MAC address and IP on your LAN, making it appear as a physical device on the network.

---

## Quick Reference

**Your Network Settings** (fill this in):

```
Network Interface: ___________  (e.g., eno1)
Network Subnet:    ___________  (e.g., 192.168.2.0/24)
Router/Gateway:    ___________  (e.g., 192.168.2.1)
Consumer IP:       ___________  (e.g., 192.168.2.200)
Device IP:         ___________  (e.g., 192.168.2.66)
```

---

## Alternative: Port Forwarding (If Macvlan Doesn't Work)

If macvlan causes issues, you can try port forwarding:

```yaml
consumer:
  network_mode: "host"
  # This gives access to TrueNAS host network
  # May work if TrueNAS is on same LAN as device
```

But this requires changing DB and Kafka hosts to `localhost`.

---

Use `docker-compose.truenas-macvlan.yml` with your network settings! 🚀
