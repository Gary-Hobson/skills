---
name: nuttx-commit-pr
description: 遵循 Apache NuttX 规范创建 git commit 和 Pull Request。当用户想要提交代码、创建 PR 或需要了解 NuttX 贡献规范时使用。强制执行 NuttX 特定的 commit 格式和 PR 模板要求。
---

# Apache NuttX Commit 和 PR 规范

为 Apache NuttX 项目创建符合规范的 git commit 和 Pull Request。

## 快速开始

```bash
# 1. 查看本地修改
git status
git diff

# 2. 暂存更改
git add <文件>

# 3. 创建符合 NuttX 规范的 commit
git commit -s -m "subsystem/component: 简短描述变更内容.

详细说明：
- 为什么需要这个变更
- 如何实现的
- 影响范围

测试环境：配置和硬件平台
"

# 4. 运行代码格式检查（必需）
./tools/checkpatch.sh -g HEAD~

# 5. 如果检查失败，修复问题后重新提交
git add <修复的文件>
git commit --amend -s
./tools/checkpatch.sh -g HEAD~
```

## Git Commit 规范

### 必需的三个组成部分

Apache NuttX **强制要求**每个 commit 包含以下三部分，否则将被自动拒绝：

#### 1. 主题行（Topic Line）- 必需

**格式**：`<功能区域前缀>: <简短上下文描述>.`

**规则**：
- 功能区域前缀 + 冒号，后接简短描述
- 必须以句号 `.` 结尾
- 使用现在时态祈使语气
- 简洁明了，说明改动内容

**示例**：
```
net/can: Add g_ prefix to can_dlc_to_len and len_to_can_dlc.
arch/arm64: Implement MPU background region support.
drivers/sensors: Fix deadlock in set_interval operation.
sched/pthread: Move pthread mutex to user-space.
boards/sim: Fix watchdog callback handling.
```

**常见功能区域前缀**：
- `arch/<架构名>`: 架构相关代码（arm, arm64, risc-v, xtensa, x86 等）
- `drivers/<驱动类型>`: 驱动程序（sensors, net, mtd, serial 等）
- `sched/<组件>`: 调度器相关
- `net/<协议>`: 网络协议栈
- `boards/<平台>`: 开发板支持
- `fs/<文件系统>`: 文件系统
- `libs/<库名>`: 库函数
- `tools/<工具>`: 构建工具
- `Documentation`: 文档更新

#### 2. 描述部分（Description）- 必需

**内容要求**：
- 详细说明**改了什么**和**为什么要改**
- 解释**如何实现**的
- 说明实现方法
- 可以使用多个句子或项目符号

**格式建议**：
```
<空行>

这个变更解决了 XXX 问题。

实现方式：
- 具体改动点 1
- 具体改动点 2
- 具体改动点 3

影响范围：
- 影响的组件或功能
- 是否有 API 变更
- 是否影响性能

相关 Issue：#12345（如果有）
```

#### 3. 签名（Signature）- 必需

**必须使用** `git commit -s` 生成：

```
Signed-off-by: 你的姓名 <有效邮箱@地址>
```

**重要**：
- 这是 Apache License 的法律要求
- 表明你有权贡献此代码
- 必须使用有效的邮箱地址

### 严格禁止的内容

**绝不能在 commit message 中包含以下内容**：

#### 禁止的标签和元数据
- `Change-Id: I...` - Gerrit 系统的 Change-ID（NuttX 使用 GitHub，不使用 Gerrit）
- `Reviewed-by:` - 这些信息由 GitHub PR 系统自动管理
- `Tested-by:` - 测试信息应在 commit 描述部分说明
- 其他代码审查系统的元数据

**原因**：
- NuttX 使用 GitHub 进行代码审查，不是 Gerrit
- 这些标签会造成混淆，且没有实际作用
- GitHub 自动跟踪审查和测试信息

**错误示例**：
```
drivers/sensors: Fix sensor deadlock issue.

This fixes the deadlock in multi-core environments.

Change-Id: I1234567890abcdef1234567890abcdef12345678
Reviewed-by: Someone <someone@example.com>

Signed-off-by: Your Name <you@example.com>
```

**正确示例**：
```
drivers/sensors: Fix sensor deadlock issue.

This fixes the deadlock in multi-core environments.

Testing: Tested on STM32F4 with multi-core configuration

Signed-off-by: Your Name <you@example.com>
```

### 完整 Commit 示例

#### 示例 1：功能增强
```
arch/arm64: Add stack alignment and size validation for CONFIG_TLS_ALIGNED.

This change introduces comprehensive stack safety mechanisms across 20+
NuttX CPU architectures by adding validation for thread-local storage
(TLS) configurations.

Implementation:
- Implements maximum stack size enforcement via TLS_MAXSTACK limits
- Replaces architecture-specific alignment constants with unified STACK_ALIGN_MASK
- Adds runtime stack size clipping to prevent overflow
- Applies consistent alignment verification across all platforms

Impact:
- No API Changes: Stack allocation interface remains unchanged
- Only activates when CONFIG_TLS_ALIGNED is enabled
- Prevents potential stack overflow conditions
- Maintains backward compatibility

Testing: Tested on ARM Cortex-A53 and RISC-V platforms

Signed-off-by: Zhang San <zhangsan@example.com>
```

#### 示例 2：Bug 修复
```
drivers/net/slip: Set serial port to raw mode to prevent character escaping.

When a serial port is configured as a console, the \n character
automatically converts to \r\n, corrupting SLIP protocol data
transmission.

Solution:
- Apply cfmakeraw() to configure the TTY in raw mode
- Disables automatic character processing that interferes with SLIP

Impact:
- File Modified: drivers/net/slip.c
- Scope: 20 additions, 0 deletions
- No breaking changes
- Restores proper SLIP functionality

Testing: Verified on ARM64 with UART and USB-to-UART adapters

Signed-off-by: Li Si <lisi@example.com>
```

#### 示例 3：重构
```
sched/pthread: Move pthread mutex from syscall to user-space.

This refactoring reduces syscall overhead and improves performance by
allowing mutex operations to execute directly in user-space with
minimal kernel involvement.

Changes:
- Six mutex lifecycle functions transitioned to user-space
- Mutex holder tracking relocated from TCB to thread-local storage
- Helper macros introduced for recursive/non-recursive modes

Performance Impact:
- 15-20% latency reduction in mutex operations
- Improved cache efficiency
- Backward compatibility maintained

Testing:
- All existing tests pass
- No kernel failures or memory corruption detected
- Multi-architecture build success

Signed-off-by: Wang Wu <wangwu@example.com>
```

## 代码格式和质量检查

### checkpatch.sh - 强制性检查工具

**所有提交到 NuttX 的 patch 都必须通过 checkpatch.sh 检查**

#### 为什么需要 checkpatch

- 确保代码风格统一
- 检查命名规范
- 验证 commit message 格式
- 检测常见编码错误
- 维护代码库质量标准

#### 基本用法

```bash
# 检查最新的一个 commit
./tools/checkpatch.sh -g HEAD~

# 检查最近的 N 个 commits
./tools/checkpatch.sh -g HEAD~N

# 检查指定的 commit 范围
./tools/checkpatch.sh -g <start-commit>..<end-commit>

# 检查当前分支相对于 master 的所有 commits
./tools/checkpatch.sh -g master..HEAD
```

#### checkpatch 检查项目

##### 1. Commit Message 检查

**必须检查项**：
- ✓ 是否有 `Signed-off-by:` 签名
- ✗ 不能包含 `Change-Id:`（Gerrit 系统特有）
- ✗ 不能包含 `Reviewed-by:`（由 GitHub 管理）
- ✗ 不能包含 `Tested-by:`（应在描述中说明）
- ✓ 主题行格式是否正确
- ✓ 主题行是否以句号结尾

**Change-Id 问题详解**：

`Change-Id` 是 Gerrit 代码审查系统使用的标识符，例如：
```
Change-Id: I1234567890abcdef1234567890abcdef12345678
```

**为什么禁止**：
- NuttX 使用 GitHub，不是 Gerrit
- Change-Id 在 GitHub 中没有任何作用
- 会让维护者困惑，以为提交者使用了错误的工作流程
- 污染 commit 历史记录

**如何避免**：
```bash
# 如果你的 git 配置了 Gerrit commit-msg hook，需要删除
rm .git/hooks/commit-msg

# 如果已经包含了 Change-Id，需要修改 commit
git commit --amend  # 手动删除 Change-Id 行
```

##### 2. 代码风格检查

**缩进和空格**：
```c
// ✗ 错误：使用 tab
	int value;

// ✓ 正确：使用 2 个空格
  int value;

// ✗ 错误：缩进不一致
  int a;
    int b;

// ✓ 正确：统一使用 2 空格缩进
  int a;
  int b;
```

**行长度**：
```c
// ✗ 错误：超过 80 字符（某些情况允许例外）
void very_long_function_name_that_exceeds_the_line_length_limit(int param1, int param2, int param3);

// ✓ 正确：适当换行
void very_long_function_name(int param1,
                              int param2,
                              int param3);
```

##### 3. 命名规范检查

**全局变量前缀**：
```c
// ✗ 错误：全局变量没有 g_ 前缀
int sensor_count;
struct device_info info;

// ✓ 正确：全局变量使用 g_ 前缀
int g_sensor_count;
struct device_info g_info;
```

**静态变量前缀**：
```c
// ✗ 错误：静态变量使用 g_ 前缀（g_ 仅用于全局变量）
static int g_local_counter;

// ✓ 正确：静态变量不需要特殊前缀或使用 s_ 前缀
static int local_counter;
// 或
static int s_local_counter;
```

**宏定义**：
```c
// ✗ 错误：宏定义使用小写
#define max_value 100

// ✓ 正确：宏定义使用大写
#define MAX_VALUE 100
```

##### 4. 注释格式检查

**函数注释**：
```c
// ✗ 错误：使用 C++ 风格注释或格式不规范
// This function does something
int do_something(void);

// ✓ 正确：使用 C 风格注释，符合 NuttX 格式
/****************************************************************************
 * Name: do_something
 *
 * Description:
 *   This function does something important.
 *
 * Input Parameters:
 *   None
 *
 * Returned Value:
 *   Returns 0 on success, negative errno on failure.
 *
 ****************************************************************************/

int do_something(void);
```

#### 处理 checkpatch 错误

##### 标准修复流程

```bash
# 1. 运行检查
./tools/checkpatch.sh -g HEAD~

# 2. 查看具体错误信息
# 输出示例：
# ERROR: Missing Signed-off-by: line
# ERROR: Change-Id is not allowed in commit message
# WARNING: line over 80 characters
# ERROR: Global variable 'sensor_data' should have 'g_' prefix

# 3. 修复代码中的问题
vim <affected-file>

# 4. 如果是 commit message 问题，修改 commit
git commit --amend

# 5. 暂存修复的文件
git add <fixed-files>

# 6. 修改 commit（如果修复了代码）
git commit --amend -s --no-edit

# 7. 再次检查
./tools/checkpatch.sh -g HEAD~

# 8. 重复直到通过
```

##### 修复 Change-Id 问题

```bash
# 方法 1：使用 git commit --amend 手动编辑
git commit --amend
# 在编辑器中删除包含 Change-Id 的行，保存退出

# 方法 2：使用 git filter-branch（批量处理多个 commits）
git filter-branch --msg-filter 'grep -v "^Change-Id:"' HEAD~N..HEAD

# 方法 3：使用 git rebase -i 交互式修改
git rebase -i HEAD~N
# 将要修改的 commit 标记为 'edit'
# 然后对每个 commit 执行：
git commit --amend  # 删除 Change-Id
git rebase --continue
```

#### checkpatch 常见错误和解决方案

| 错误信息 | 原因 | 解决方案 |
|---------|------|---------|
| `Missing Signed-off-by` | 缺少签名 | 使用 `git commit --amend -s` |
| `Change-Id is not allowed` | 包含 Gerrit Change-Id | 修改 commit 删除 Change-Id 行 |
| `line over 80 characters` | 行太长 | 适当换行，或使用变量简化表达式 |
| `Global variable should have 'g_' prefix` | 全局变量命名不规范 | 添加 `g_` 前缀 |
| `Use C89 style comments` | 使用了 C++ 风格注释 | 改为 `/* */` 格式 |
| `Improper spacing` | 空格使用不当 | 调整空格位置 |
| `Tab indentation` | 使用了 tab 缩进 | 改为 2 个空格 |

#### 集成到工作流程

**推荐的工作流程**：

```bash
# 1. 开发和修改代码
vim <files>

# 2. 提交更改
git add <files>
git commit -s -m "subsystem: description.

Details...

Signed-off-by: Your Name <email>"

# 3. 立即运行 checkpatch（不要等到推送时）
./tools/checkpatch.sh -g HEAD~

# 4. 如果有错误，立即修复
# ... 修复代码 ...
git add <fixed-files>
git commit --amend -s --no-edit

# 5. 再次检查
./tools/checkpatch.sh -g HEAD~

# 6. 通过后再推送
git push origin <branch>
```

**使用 git hook 自动检查**（可选）：

```bash
# 创建 pre-push hook
cat > .git/hooks/pre-push << 'EOF'
#!/bin/bash
echo "Running checkpatch before push..."
./tools/checkpatch.sh -g origin/master..HEAD
if [ $? -ne 0 ]; then
  echo "Checkpatch failed! Please fix the issues before pushing."
  exit 1
fi
EOF

chmod +x .git/hooks/pre-push
```

### 完整示例：错误 vs 正确

#### ❌ 错误示例（会被 checkpatch 拒绝）

```
drivers/sensors: fix bug

Fixed the sensor issue

Change-Id: I1234567890abcdef1234567890abcdef12345678
Reviewed-by: Someone <someone@example.com>
```

**问题**：
1. 主题行没有以句号结尾
2. 描述太简略，没有说明什么 bug、如何修复
3. 包含了 Change-Id（Gerrit 系统标识）
4. 包含了 Reviewed-by（应由 GitHub 管理）
5. 没有 Signed-off-by 签名

**checkpatch 输出**：
```
ERROR: Missing Signed-off-by: line
ERROR: Change-Id is not allowed in commit message
ERROR: Reviewed-by is not allowed in commit message
WARNING: Commit message should end with period
WARNING: Commit description too short
```

#### ✅ 正确示例（通过 checkpatch）

```
drivers/sensors: Fix deadlock in multi-core sensor operations.

When multiple threads access sensor drivers concurrently in multi-core
environments, a deadlock can occur due to lock holding during lower-half
driver operations.

Solution:
- Release upper layer lock before calling lower-half operations
- Use atomic operations for state management
- Implement proper lock ordering to prevent circular dependencies

Impact:
- Fixes system hangs in sensor-intensive applications
- Improves sensor driver scalability on multi-core systems
- No API changes, maintains backward compatibility

Testing: Verified on STM32F4 (Cortex-M4) with concurrent sensor access,
no deadlocks observed after 10000 iterations.

Signed-off-by: Zhang San <zhangsan@example.com>
```

**checkpatch 输出**：
```
$ ./tools/checkpatch.sh -g HEAD~
Checking patch 1/1: drivers/sensors: Fix deadlock in multi-core sensor operations...
✓ All checks passed
```

**为什么正确**：
1. ✓ 主题行以句号结尾
2. ✓ 详细描述了问题、解决方案和影响
3. ✓ 没有 Change-Id 或其他审查系统标签
4. ✓ 包含 Signed-off-by 签名
5. ✓ 说明了测试环境和结果

## Pull Request 规范

### PR 模板结构

Apache NuttX 要求 PR 包含以下**必需章节**：

#### 1. Summary（概述）- 必需

说明：
- **为什么**需要这个变更（必要性）
- 影响了哪些代码区域
- 实现方法
- 相关 Issue 引用（如果有）

**示例**：
```markdown
## Summary

This PR fixes a critical deadlock issue in the sensor subsystem that occurs
in multi-core environments when multiple threads access sensor drivers
concurrently.

### Changes:
- Remove lock holding during lower-half driver operations
- Release locks before RPMSG communication to prevent deadlock
- Replace recursive mutexes with read-write semaphores for better scalability

### Related Issues:
Fixes #12345
```

#### 2. Impact（影响评估）- 必需

必须说明对以下方面的影响：
- 功能变更（Features）
- 用户体验（User experience）
- 构建过程（Build process）
- 硬件支持（Hardware support）
- 文档（Documentation）
- 安全性（Security）
- 兼容性（Compatibility）

**示例**：
```markdown
## Impact

- **Features**: Adds new MTD config device support for NVS testing
- **API Changes**: None - maintains backward compatibility
- **Build**: No build system changes required
- **Hardware**: Enables new device types for QEMU testing
- **Documentation**: No documentation updates needed for this change
- **Security**: No security implications
- **Compatibility**: Fully backward compatible, no breaking changes
```

#### 3. Testing（测试验证）- 必需

**强制要求**：
- 必须在**真实硬件**上进行本地测试
- 必须提供构建日志（build logs）
- 必须提供运行日志（runtime logs）
- 必须展示修改前后的对比结果
- **必须运行** `./tools/checkpatch.sh` **并通过所有检查**

**示例**：
```markdown
## Testing

### Test Configuration:
- **Board**: STM32F4Discovery
- **Config**: nsh configuration with CONFIG_SENSORS enabled
- **Build**: `make distclean && ./tools/configure.sh stm32f4discovery:nsh && make`

### Build Logs:
```
CC:  sensor/sensor_upper.c
LD:  nuttx
   text    data     bss     dec     hex filename
 123456    5678    9012  138146   21ba2 nuttx
```

### Runtime Logs:

**Before fix**: System hangs when multiple sensor operations occur
```
nsh> sensor_test
[  5.123] sensor: deadlock detected
[stuck]
```

**After fix**: All operations complete successfully
```
nsh> sensor_test
[  5.123] sensor: flush completed
[  5.234] sensor: data streaming OK
[  5.345] sensor: all tests passed
```

### Hardware Tested:
- [x] STM32F4Discovery (ARM Cortex-M4)
- [x] ESP32-C3 (RISC-V)
- [ ] Simulator (not applicable for this hardware-specific fix)

### Code Style Check:
```bash
$ ./tools/checkpatch.sh -g HEAD~
✓ All checks passed
```
```

#### 4. 文档更新 - 如适用

**规则**：文档变更必须包含在同一个 PR 中

如果代码变更影响了：
- 用户 API
- 配置选项
- 硬件支持
- 构建过程

则必须同时更新相应文档。

### 完整 PR 示例

#### 标题格式
```
<功能区域>: <简短描述>
```

**示例**：
- `arch/arm64: MPU enhancements and protected mode support`
- `drivers/sensors: fix sensor deadlock in multi-core environments`
- `sched/pthread: move pthread mutex to user-space`

#### PR 描述模板

```markdown
## Summary

[必需] 3-5 句话说明：
- 这个 PR 解决什么问题
- 为什么需要这个变更
- 主要实现了什么功能

### Changes:
- 变更点 1
- 变更点 2
- 变更点 3

### Related Issues:
Fixes #issue_number

## Impact

- **Features**: [描述功能影响]
- **User Experience**: [描述用户体验变化]
- **Build**: [描述构建影响]
- **Hardware**: [描述硬件支持变化]
- **Documentation**: [说明文档是否需要更新]
- **Security**: [说明安全影响]
- **Compatibility**: [说明兼容性影响]

## Testing

### Test Configuration:
- **Board**: [硬件平台名称]
- **Architecture**: [CPU 架构]
- **Config**: [使用的配置]
- **Toolchain**: [工具链版本]

### Build Command:
```bash
make distclean
./tools/configure.sh <board>:<config>
make
```

### Build Logs:
```
[构建输出日志]
```

### Runtime Test Results:

**Before this PR:**
```
[修改前的运行日志，展示问题]
```

**After this PR:**
```
[修改后的运行日志，展示修复效果]
```

### Hardware Platforms Tested:
- [x] Platform 1 (Architecture)
- [x] Platform 2 (Architecture)
- [ ] Platform 3 (not tested - reason)

### Code Style Check:
```bash
$ ./tools/checkpatch.sh -g HEAD~3
Checking patch 1/3: subsystem: first commit...
✓ All checks passed

Checking patch 2/3: subsystem: second commit...
✓ All checks passed

Checking patch 3/3: subsystem: third commit...
✓ All checks passed
```

## Documentation

[如适用] 说明文档更新情况：
- Updated: Documentation/path/to/doc.rst
- Added: Documentation/components/new-feature.rst
- N/A: No documentation changes needed
```

## 工作流程

### 创建 Commit

```bash
# 1. 查看修改
git status
git diff

# 2. 暂存文件
git add <具体文件>  # 推荐
# 或
git add -A  # 暂存所有修改

# 3. 创建 commit（使用 -s 自动添加签名）
git commit -s -m "$(cat <<'EOF'
subsystem/component: Brief description of change.

Detailed explanation of what changed and why.

Implementation:
- Detail 1
- Detail 2

Impact:
- What areas are affected
- Any API changes

Testing: Hardware platform and configuration used
EOF
)"

# 4. 运行代码格式检查（必需！）
./tools/checkpatch.sh -g HEAD~

# 5. 如果检查失败，修复问题
# 修复代码格式问题后：
git add <修复的文件>
git commit --amend -s --no-edit
./tools/checkpatch.sh -g HEAD~

# 6. 验证 commit
git log -1
git show HEAD
```

### 代码格式检查（checkpatch）- 必需

**NuttX 要求所有 patch 必须通过 checkpatch.sh 检查**

#### 检查命令

```bash
# 检查最新的 commit
./tools/checkpatch.sh -g HEAD~

# 检查最近 N 个 commits
./tools/checkpatch.sh -g HEAD~N

# 检查指定范围的 commits
./tools/checkpatch.sh -g <commit-hash>~..<commit-hash>
```

#### 常见检查项

checkpatch.sh 会检查以下内容：

1. **代码风格**
   - 缩进（使用 2 空格，不是 tab）
   - 行长度（一般不超过 80 字符）
   - 空格和空行的使用
   - 括号和花括号的位置

2. **命名规范**
   - 全局变量必须使用 `g_` 前缀
   - 静态变量使用适当前缀
   - 宏定义使用大写

3. **注释格式**
   - C 风格注释格式
   - 函数头注释格式

4. **Commit Message**
   - 检查是否包含禁止的 Change-Id
   - 检查是否有 Signed-off-by

#### 修复 checkpatch 错误的流程

```bash
# 1. 运行检查，查看错误
./tools/checkpatch.sh -g HEAD~

# 2. 根据错误信息修复代码
# 例如：修复缩进、添加 g_ 前缀、删除 Change-Id 等

# 3. 暂存修复的文件
git add <修复的文件>

# 4. 修改 commit（不改变 commit message）
git commit --amend -s --no-edit

# 5. 再次检查
./tools/checkpatch.sh -g HEAD~

# 6. 重复步骤 2-5 直到检查通过
```

#### 自动修复部分问题

某些格式问题可以使用工具自动修复：

```bash
# 使用 nxstyle 检查和提示修复建议
./tools/nxstyle.sh <文件路径>

# 注意：需要手动应用修复建议
```

### 创建 Pull Request

```bash
# 1. 确保代码已推送
git push origin <branch-name>

# 2. 创建 PR（使用 GitHub CLI）
gh pr create --title "subsystem: brief description" --body "$(cat <<'EOF'
## Summary

[描述变更内容和原因]

### Changes:
- 变更点 1
- 变更点 2

## Impact

- **Features**: [影响说明]
- **Build**: [影响说明]
- **Compatibility**: [影响说明]

## Testing

### Test Configuration:
- **Board**: [硬件平台]
- **Config**: [配置]

### Build Logs:
```
[构建日志]
```

### Runtime Logs:
```
[运行日志]
```

### Hardware Tested:
- [x] Platform 1
EOF
)"

# 3. 运行 checkpatch 检查（必需！）
./tools/checkpatch.sh -g HEAD~

# 4. 如果检查失败，修复问题后重新检查
```

## 重要规则

### Commit 规则
- **必须**使用 `git commit -s` 添加签名
- **必须**包含功能区域前缀和冒号
- **必须**以句号结尾主题行
- **必须**提供详细的描述部分
- **必须**在提交前运行 `./tools/checkpatch.sh -g HEAD~` 检查
- **必须**修复所有 checkpatch 报告的错误
- **绝不**使用模糊的描述（如 "fix bug", "update code"）
- **绝不**遗漏签名（Signed-off-by）
- **绝不**提交机密信息或凭证
- **绝不**包含 Change-Id 或其他审查系统的元数据

### PR 规则
- **必须**在真实硬件上测试
- **必须**提供构建和运行日志
- **必须**说明对各方面的影响
- **必须**包含前后对比的测试结果
- **必须**同时提交相关的文档更新
- **必须**运行 `./tools/checkpatch.sh` 并通过所有检查
- **绝不**提交未经测试的代码
- **绝不**跳过 Impact 评估
- **绝不**遗漏 Testing 章节
- **绝不**提交包含 Change-Id 的 commit

### 质量标准
- 每个 PR 专注于单一功能变更
- 多个 commit 可以接受，但每个都必须保持构建和运行兼容性
- 进行中的 PR 使用 `[WIP]` 标签并设为草稿
- 不要使用 `--no-verify` 或 `--no-gpg-sign` 等跳过检查的选项
- 永远不要使用 `git commit --amend` 除非明确需要

## 常见功能区域示例

### 架构相关
```
arch/arm: 描述 ARM 架构相关变更.
arch/arm64: 描述 ARM64 架构相关变更.
arch/risc-v: 描述 RISC-V 架构相关变更.
arch/xtensa: 描述 Xtensa 架构相关变更.
arch/x86_64: 描述 x86_64 架构相关变更.
```

### 驱动程序
```
drivers/sensors: 描述传感器驱动相关变更.
drivers/net: 描述网络驱动相关变更.
drivers/serial: 描述串口驱动相关变更.
drivers/mtd: 描述 MTD 设备驱动相关变更.
drivers/usb: 描述 USB 驱动相关变更.
```

### 系统组件
```
sched/pthread: 描述 pthread 调度相关变更.
sched/task: 描述任务调度相关变更.
net/tcp: 描述 TCP 协议栈相关变更.
net/udp: 描述 UDP 协议栈相关变更.
fs/vfs: 描述虚拟文件系统相关变更.
```

### 开发板支持
```
boards/sim: 描述模拟器平台相关变更.
boards/arm/stm32: 描述 STM32 开发板相关变更.
boards/risc-v/esp32c3: 描述 ESP32-C3 开发板相关变更.
```

## 提交前检查清单

在创建 PR 或推送 commits 之前，请确认以下所有项目：

### Commit Message 检查清单

- [ ] 主题行包含正确的功能区域前缀（如 `drivers/sensors:`）
- [ ] 主题行以句号 `.` 结尾
- [ ] 主题行使用现在时态祈使语气
- [ ] 包含详细的描述部分，说明了为什么和如何
- [ ] 包含 `Signed-off-by:` 签名（使用 `git commit -s`）
- [ ] **没有** `Change-Id:` 行
- [ ] **没有** `Reviewed-by:` 或 `Tested-by:` 等其他审查系统标签
- [ ] 运行了 `./tools/checkpatch.sh -g HEAD~` 并通过

### 代码质量检查清单

- [ ] 使用 2 个空格缩进（不是 tab）
- [ ] 全局变量使用 `g_` 前缀
- [ ] 宏定义使用大写字母
- [ ] 使用 C89 风格注释 `/* */`（不是 `//`）
- [ ] 代码行长度合理（一般不超过 80 字符）
- [ ] 函数有适当的注释说明

### 测试检查清单

- [ ] 在真实硬件上测试（不仅仅是编译通过）
- [ ] 准备了构建日志
- [ ] 准备了运行日志（修改前后对比）
- [ ] 记录了测试使用的硬件平台和配置

### PR 检查清单

- [ ] PR 标题使用正确格式：`功能区域: 简短描述`
- [ ] PR 描述包含 Summary、Impact、Testing 三个必需章节
- [ ] 列出了所有影响的方面（Features, Build, Compatibility 等）
- [ ] 提供了详细的测试结果和日志
- [ ] 包含了 checkpatch 检查通过的证明
- [ ] 如果影响了 API，同时更新了文档

## 参考资源

- [NuttX Contributing Guide](https://github.com/apache/nuttx/blob/master/CONTRIBUTING.md)
- [Apache License Contributor Agreement](https://www.apache.org/licenses/contributor-agreements.html)
- [NuttX Coding Style](https://nuttx.apache.org/docs/latest/contributing/coding_style.html)
- [checkpatch.sh 工具](https://github.com/apache/nuttx/blob/master/tools/checkpatch.sh)

## 与其他技能的集成

本技能专门针对 Apache NuttX 项目。如果在其他项目中工作，使用通用的 `git-commit` 和 `github-pr-creation` 技能。

### 何时使用此技能
- 为 Apache NuttX 或 NuttX Apps 仓库贡献代码
- 需要遵循 NuttX 特定的 commit 格式
- 创建需要硬件测试证明的 PR
- 提交需要 Signed-off-by 的 Apache License 项目

### 何时使用其他技能
- 通用 Git 项目：使用 `git-commit`
- 通用 GitHub PR：使用 `github-pr-creation`
- 代码审查：使用 `github-pr-review`
- 合并 PR：使用 `github-pr-merge`
