#!/usr/bin/env python3
"""重置密码脚本"""
import sys
import os
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.core.config import Config
import getpass

def reset_password():
    """重置密码"""
    print("=" * 50)
    print("Lookoukwindow 密码重置工具")
    print("=" * 50)
    
    config = Config()
    
    # 检查是否已设置密码
    if config.is_password_set():
        password_hash = config.get('security.login_password_hash')
        plain_password = config.get('security.login_password')
        
        print(f"\n当前状态:")
        print(f"  - 密码hash存在: {bool(password_hash)}")
        print(f"  - 明文密码存在: {bool(plain_password)}")
        
        if password_hash:
            print(f"  - 密码hash: {password_hash[:20]}...")
        
        confirm = input("\n确定要重置密码吗？(yes/no): ").strip().lower()
        if confirm != 'yes':
            print("已取消重置")
            return
        
        # 清除现有密码
        config.set('security.login_password_hash', '')
        config.set('security.login_password', '')
        config.save()
        print("\n✓ 已清除旧密码")
    else:
        print("\n当前未设置密码")
    
    # 设置新密码
    print("\n请设置新密码:")
    while True:
        password = getpass.getpass("密码: ")
        if len(password) < 6:
            print("密码长度至少6位，请重新输入")
            continue
        
        password_bytes = len(password.encode('utf-8'))
        if password_bytes > 72:
            print(f"密码长度不能超过72字节（当前: {password_bytes} 字节），请重新输入")
            continue
        
        password_confirm = getpass.getpass("确认密码: ")
        if password != password_confirm:
            print("两次输入的密码不一致，请重新输入")
            continue
        
        break
    
    # 保存新密码
    try:
        config.set_password(password)
        print("\n✓ 密码设置成功！")
        print("\n现在可以使用新密码登录了")
    except Exception as e:
        print(f"\n✗ 密码设置失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    try:
        reset_password()
    except KeyboardInterrupt:
        print("\n\n已取消操作")
        sys.exit(0)
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
