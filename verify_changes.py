#!/usr/bin/env python3
"""验证 OpenSpec 集成的更改"""

import os
import sys
from pathlib import Path

def test_openspec_file_structure():
    """测试 OpenSpec 文件结构"""
    print("✓ 测试 OpenSpec 工具文件存在...")
    openspec_file = Path("crewforge/tools/openspec.py")
    assert openspec_file.exists(), "openspec.py 不存在"
    print(f"  ✓ {openspec_file} 存在")
    return True

def test_imports():
    """测试导入语法"""
    print("\n✓ 测试导入语法...")

    files_to_check = [
        "crewforge/tools/openspec.py",
        "crewforge/tools/__init__.py",
        "crewforge/core/agents/architect.py",
        "crewforge/core/agents/developer.py",
        "crewforge/config/settings.py",
        "crewforge/cli.py",
        "crewforge/core/crew.py",
    ]

    import ast
    for file_path in files_to_check:
        with open(file_path, 'r', encoding='utf-8') as f:
            try:
                ast.parse(f.read())
                print(f"  ✓ {file_path} 语法正确")
            except SyntaxError as e:
                print(f"  ✗ {file_path} 语法错误: {e}")
                return False
    return True

def test_openspec_content():
    """测试 OpenSpec 工具内容"""
    print("\n✓ 测试 OpenSpec 工具类...")

    with open("crewforge/tools/openspec.py", 'r') as f:
        content = f.read()

    # 检查关键类是否存在
    expected_classes = [
        "OpenSpecWriterTool",
        "OpenSpecReaderTool",
        "OpenSpecUpdateTool",
        "get_openspec_tools"
    ]

    for class_name in expected_classes:
        if class_name in content:
            print(f"  ✓ 找到 {class_name}")
        else:
            print(f"  ✗ 未找到 {class_name}")
            return False

    return True

def test_architect_integration():
    """测试 Architect agent 集成"""
    print("\n✓ 测试 Architect agent OpenSpec 集成...")

    with open("crewforge/core/agents/architect.py", 'r') as f:
        content = f.read()

    checks = [
        ("get_openspec_tools", "导入 OpenSpec 工具"),
        ("SPEC.md", "提及 SPEC.md"),
        ("PLAN.md", "提及 PLAN.md"),
        ("spec-driven development", "提及规范驱动开发"),
    ]

    for check_str, description in checks:
        if check_str in content:
            print(f"  ✓ {description}")
        else:
            print(f"  ✗ 未找到: {description}")
            return False

    return True

def test_developer_integration():
    """测试 Developer agent 集成"""
    print("\n✓ 测试 Developer agent OpenSpec 集成...")

    with open("crewforge/core/agents/developer.py", 'r') as f:
        content = f.read()

    checks = [
        ("get_openspec_tools", "导入 OpenSpec 工具"),
        ("SPEC.md", "提及 SPEC.md"),
        ("OpenSpec", "提及 OpenSpec"),
    ]

    for check_str, description in checks:
        if check_str in content:
            print(f"  ✓ {description}")
        else:
            print(f"  ✗ 未找到: {description}")
            return False

    return True

def test_orchestrator_integration():
    """测试 Orchestrator 集成"""
    print("\n✓ 测试 CrewForgeOrchestrator OpenSpec 集成...")

    with open("crewforge/core/crew.py", 'r') as f:
        content = f.read()

    checks = [
        ("_read_openspec_context", "OpenSpec 上下文读取方法"),
        ("write_openspec", "write_openspec 工具引用"),
        ("SPEC.md", "SPEC.md 引用"),
        ("PLAN.md", "PLAN.md 引用"),
    ]

    for check_str, description in checks:
        if check_str in content:
            print(f"  ✓ {description}")
        else:
            print(f"  ✗ 未找到: {description}")
            return False

    return True

def test_settings():
    """测试配置设置"""
    print("\n✓ 测试 OpenSpec 配置...")

    with open("crewforge/config/settings.py", 'r') as f:
        content = f.read()

    checks = [
        ("openspec_enabled", "openspec_enabled 配置"),
        ("openspec_dir", "openspec_dir 配置"),
        ("openspec_auto_update", "openspec_auto_update 配置"),
    ]

    for check_str, description in checks:
        if check_str in content:
            print(f"  ✓ {description}")
        else:
            print(f"  ✗ 未找到: {description}")
            return False

    return True

def test_cli_chinese():
    """测试 CLI 中文化"""
    print("\n✓ 测试 CLI 中文化...")

    with open("crewforge/cli.py", 'r', encoding='utf-8') as f:
        content = f.read()

    # 检查一些关键的中文字符串
    chinese_checks = [
        "初始化新的 CrewForge 项目",
        "启动开发流程",
        "恢复之前中断的项目",
        "显示项目状态",
        "列出项目的任务列表",
    ]

    for chinese_str in chinese_checks:
        if chinese_str in content:
            print(f"  ✓ 找到中文: {chinese_str}")
        else:
            print(f"  ✗ 未找到中文: {chinese_str}")
            return False

    return True

def test_documentation():
    """测试文档更新"""
    print("\n✓ 测试 CLAUDE.md 文档更新...")

    with open("CLAUDE.md", 'r') as f:
        content = f.read()

    checks = [
        ("OpenSpec", "OpenSpec 提及"),
        ("spec-driven development", "规范驱动开发"),
        ("SPEC.md", "SPEC.md 文档"),
        ("PLAN.md", "PLAN.md 文档"),
    ]

    for check_str, description in checks:
        if check_str in content:
            print(f"  ✓ {description}")
        else:
            print(f"  ✗ 未找到: {description}")
            return False

    return True

def main():
    """运行所有验证测试"""
    print("=" * 60)
    print("CrewForge OpenSpec 集成验证")
    print("=" * 60)

    tests = [
        test_openspec_file_structure,
        test_imports,
        test_openspec_content,
        test_architect_integration,
        test_developer_integration,
        test_orchestrator_integration,
        test_settings,
        test_cli_chinese,
        test_documentation,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
                print(f"\n  ✗ {test.__name__} 失败")
        except Exception as e:
            failed += 1
            print(f"\n  ✗ {test.__name__} 出错: {e}")

    print("\n" + "=" * 60)
    print(f"测试结果: {passed} 通过, {failed} 失败")
    print("=" * 60)

    if failed == 0:
        print("\n✅ 所有验证测试通过！")
        return 0
    else:
        print(f"\n❌ {failed} 个测试失败")
        return 1

if __name__ == "__main__":
    sys.exit(main())
