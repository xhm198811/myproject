import socket

def get_local_ip():
    try:
        # 创建一个UDP套接字
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # 连接到一个外部地址（不需要实际连接）
        s.connect(("8.8.8.8", 80))
        # 获取本地IP地址
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except Exception as e:
        print(f"获取本地IP失败: {e}")
        return "127.0.0.1"

if __name__ == "__main__":
    ip = get_local_ip()
    print(f"本地IP地址: {ip}")