#!/usr/bin/env python3
"""
Phase 2 Chat UI Verification Script
验证 Chat UI 前端实现的完整性
"""

import json
from pathlib import Path

# 颜色代码
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
RESET = "\033[0m"


def check_file_exists(filepath: str) -> bool:
    """检查文件是否存在"""
    exists = Path(filepath).exists()
    status = f"{GREEN}✓{RESET}" if exists else f"{RED}✗{RESET}"
    print(f"  {status} {filepath}")
    return exists


def check_file_content(filepath: str, required_strings: list[str]) -> bool:
    """检查文件是否包含必需的字符串"""
    try:
        with open(filepath, encoding="utf-8") as f:
            content = f.read()

        missing = []
        for req in required_strings:
            if req not in content:
                missing.append(req)

        if missing:
            print(f"  {RED}✗{RESET} {filepath} - Missing: {missing}")
            return False
        else:
            print(f"  {GREEN}✓{RESET} {filepath} - All required content present")
            return True
    except Exception as e:
        print(f"  {RED}✗{RESET} {filepath} - Error: {e}")
        return False


def main():
    print("=" * 60)
    print("Phase 2 Chat UI Verification")
    print("=" * 60)

    base_path = Path("/home/shuhao/SAGE/packages/sage-studio/src/sage/studio/frontend")

    all_passed = True

    # 1. 检查新增文件
    print("\n[1] Checking new files...")
    new_files = [
        "src/store/chatStore.ts",
        "src/components/ChatMode.tsx",
    ]

    for file in new_files:
        full_path = base_path / file
        if not check_file_exists(str(full_path)):
            all_passed = False

    # 2. 检查 chatStore.ts 关键内容
    print("\n[2] Verifying chatStore.ts...")
    chatstore_checks = [
        "useChatStore",
        "ChatMessage",
        "ChatSession",
        "setCurrentSessionId",
        "addMessage",
        "appendToMessage",
        "setIsStreaming",
    ]
    if not check_file_content(str(base_path / "src/store/chatStore.ts"), chatstore_checks):
        all_passed = False

    # 3. 检查 ChatMode.tsx 关键内容
    print("\n[3] Verifying ChatMode.tsx...")
    chatmode_checks = [
        "useChatStore",
        "sendChatMessage",
        "getChatSessions",
        "deleteChatSession",
        "handleSendMessage",
        "New Chat",
        "SSE",
    ]
    if not check_file_content(str(base_path / "src/components/ChatMode.tsx"), chatmode_checks):
        all_passed = False

    # 4. 检查 App.tsx 模式切换
    print("\n[4] Verifying App.tsx mode switching...")
    app_checks = [
        "AppMode",
        "mode",
        "setMode",
        "ChatMode",
        "builder",
        "chat",
    ]
    if not check_file_content(str(base_path / "src/App.tsx"), app_checks):
        all_passed = False

    # 5. 检查 Toolbar.tsx 集成
    print("\n[5] Verifying Toolbar.tsx integration...")
    toolbar_checks = [
        "ToolbarProps",
        "mode",
        "onModeChange",
        "Segmented",
        "Builder",
        "Chat",
    ]
    if not check_file_content(str(base_path / "src/components/Toolbar.tsx"), toolbar_checks):
        all_passed = False

    # 6. 检查 api.ts Chat API
    print("\n[6] Verifying api.ts Chat API methods...")
    api_checks = [
        "sendChatMessage",
        "getChatSessions",
        "deleteChatSession",
        "ChatSession",
        "/chat/message",
        "/chat/sessions",
    ]
    if not check_file_content(str(base_path / "src/services/api.ts"), api_checks):
        all_passed = False

    # 7. 检查 package.json zustand 依赖
    print("\n[7] Verifying package.json dependencies...")
    package_json_path = base_path / "package.json"
    try:
        with open(package_json_path) as f:
            pkg = json.load(f)

        if "zustand" in pkg.get("dependencies", {}):
            print(f"  {GREEN}✓{RESET} zustand dependency found")
        else:
            print(f"  {RED}✗{RESET} zustand dependency missing")
            all_passed = False
    except Exception as e:
        print(f"  {RED}✗{RESET} Failed to read package.json: {e}")
        all_passed = False

    # 8. 检查测试文档
    print("\n[8] Verifying test documentation...")
    test_doc_path = Path("/home/shuhao/SAGE/packages/sage-studio/TEST_CHAT_UI.md")
    if not check_file_exists(str(test_doc_path)):
        all_passed = False

    # 最终结果
    print("\n" + "=" * 60)
    if all_passed:
        print(f"{GREEN}✅ All checks passed!{RESET}")
        print(f"\n{YELLOW}Next steps:{RESET}")
        print("  1. Run chat mode: sage studio chat start")
        print("  2. Open browser: http://localhost:5173")
        print("  3. Switch to 'Chat' tab in the toolbar")
        print("  4. Use 'sage studio chat stop' to shut everything down")
        return 0
    else:
        print(f"{RED}❌ Some checks failed. Please review the errors above.{RESET}")
        return 1


if __name__ == "__main__":
    exit(main())
