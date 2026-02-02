"""Test connection with explicit timeout and better error handling."""
import asyncio
import socket

async def test_with_timeout():
    """Test DNS resolution with detailed debugging."""
    print("=== Debugging DNS Resolution ===\n")
    
    host = "db.nfgnxndktecqeleabbip.supabase.co"
    port = 6543
    
    # Test 1: Socket getaddrinfo (what asyncpg uses internally)
    print(f"Test 1: socket.getaddrinfo('{host}', {port})")
    try:
        result = socket.getaddrinfo(host, port, socket.AF_UNSPEC, socket.SOCK_STREAM)
        print(f"[SUCCESS] Found {len(result)} address(es):")
        for addr_info in result:
            family, socktype, proto, canonname, sockaddr = addr_info
            family_name = "IPv4" if family == socket.AF_INET else "IPv6" if family == socket.AF_INET6 else "Unknown"
            print(f"  - {family_name}: {sockaddr[0]}:{sockaddr[1]}")
    except Exception as e:
        print(f"[ERROR] {type(e).__name__}: {e}")
        return False
    
    # Test 2: Force IPv4 only
    print(f"\nTest 2: Force IPv4 only")
    try:
        result = socket.getaddrinfo(host, port, socket.AF_INET, socket.SOCK_STREAM)
        if result:
            ipv4_addr = result[0][4][0]
            print(f"[SUCCESS] IPv4 address: {ipv4_addr}")
            
            # Test 3: Try connecting via asyncpg with IPv4
            print(f"\nTest 3: Connect via asyncpg using IPv4 address")
            import asyncpg
            
            conn = await asyncpg.connect(
                host=ipv4_addr,  # Use IP directly
                port=port,
                user="postgres",
                password="vZ/jU+4/QuVJYCd",
                database="postgres",
                ssl="require",
                timeout=30
            )
            
            version = await conn.fetchval('SELECT version();')
            print(f"[SUCCESS] Connected via IP!")
            print(f"PostgreSQL version: {version[:50]}...")
            await conn.close()
            
            print(f"\n>> SOLUTION: Use IP address {ipv4_addr} instead of hostname")
            return ipv4_addr
            
    except socket.gaierror as e:
        print(f"[ERROR] IPv4 resolution failed: {e}")
        return False
    except Exception as e:
        print(f"[ERROR] Connection failed: {type(e).__name__}: {e}")
        return False

if __name__ == "__main__":
    result = asyncio.run(test_with_timeout())
    if result:
        print(f"\n✓ Use this in your DATABASE_URL:")
        print(f"  postgresql+asyncpg://postgres:PASSWORD@{result}:6543/postgres")
