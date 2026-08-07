# 可视化浏览器自动化参考

本文件存放 `visible-browser-form-automation` 的实现细节。主 Skill 只在需要建立 WSL → Windows Chrome 的 CDP 通路、检查动态表单或处理上传控件时加载本参考。

## 1. Windows Chrome 启动模式

先探测 Chrome 的实际路径。常见位置包括：

```text
C:\Program Files\Google\Chrome\Application\chrome.exe
C:\Program Files (x86)\Google\Chrome\Application\chrome.exe
```

从 WSL 调用时，对应路径通常位于 `/mnt/c/Program Files/...`。

建议使用独立 profile：

```powershell
Start-Process "C:\Program Files\Google\Chrome\Application\chrome.exe" -ArgumentList @(
  "--remote-debugging-port=9222",
  "--user-data-dir=C:\Temp\agent-browser",
  "https://example.com"
)
```

不要对用户默认 Chrome profile 直接开放 CDP。现代 Chrome 也会限制对默认数据目录使用远程调试参数，因此专用 `--user-data-dir` 同时是安全和兼容性要求。

## 2. 从 WSL 验证 CDP

```bash
curl -s http://localhost:9222/json/version
curl -s http://localhost:9222/json/list
```

`/json/version` 应包含：

```text
Browser
Protocol-Version
webSocketDebuggerUrl
```

`/json/list` 中寻找：

```text
type: page
url: 目标网址
webSocketDebuggerUrl: ws://127.0.0.1:9222/devtools/page/...
```

如果存在浏览器扩展 background page、service worker、omnibox popup，不要误把它们当成目标标签页。

## 3. 没有 Playwright 时直接调用 CDP

Python 环境中已有 `websocket-client` 时，可以连接页面级 WebSocket。CDP 消息基本结构为：

```json
{"id":1,"method":"Runtime.evaluate","params":{"expression":"document.title","returnByValue":true}}
```

常用命令包括：

```text
Runtime.enable
Runtime.evaluate
Page.enable
Page.navigate
DOM.enable
DOM.getDocument
DOM.querySelector
DOM.setFileInputFiles
```

对于简单表单，`Runtime.evaluate` 足以完成大部分勘察、点击、赋值、滚动和状态验证。

## 4. 页面勘察表达式

读取可见正文：

```javascript
document.body.innerText
```

枚举表单控件：

```javascript
[...document.querySelectorAll('input, textarea, select, button')].map((el, i) => ({
  i,
  tag: el.tagName,
  type: el.type || '',
  id: el.id || '',
  name: el.name || '',
  value: el.value || '',
  placeholder: el.placeholder || '',
  readonly: !!el.readOnly,
  checked: !!el.checked,
  multiple: !!el.multiple,
  accept: el.accept || ''
}))
```

检查题目容器是否显示：

```javascript
[...document.querySelectorAll('[id^="div"]')].map(el => ({
  id: el.id,
  display: getComputedStyle(el).display,
  visibility: getComputedStyle(el).visibility,
  text: el.innerText.slice(0, 200)
}))
```

不要依赖某个站点一定使用 `div1`、`q1` 这类命名；先观察再建立当前页面映射。

## 5. 填写普通输入框

需要让页面监听到变更时，不只设置 `value`，还要触发事件：

```javascript
const el = document.querySelector('#q1');
el.focus();
el.value = '示例';
el.dispatchEvent(new Event('input', { bubbles: true }));
el.dispatchEvent(new Event('change', { bubbles: true }));
el.blur();
```

如果框架重写了原生 setter，可以调用 `HTMLInputElement.prototype` 上的 setter，再派发事件。

## 6. 单选和条件题

优先让页面自己的点击逻辑生效：

```javascript
document.querySelector('#q2_1')?.click();
```

如果真实 `input` 被隐藏而点击绑定在包装元素上，应点击站点实际监听的 label、anchor 或 wrapper。点击后重新读取后续题目的 `display` 状态。

不要一次性给所有隐藏题写值再假定页面会接受；条件题应按真实交互顺序展开。

## 7. 日期控件

对只读日期输入框，首选点击页面日期选择器。如果必须直接设置，应在设置后验证站点是否接受：

```javascript
const el = document.querySelector('#date');
el.removeAttribute('readonly');
el.value = '2026-08-07';
el.dispatchEvent(new Event('input', { bubbles: true }));
el.dispatchEvent(new Event('change', { bubbles: true }));
```

不要把这一方式当作默认做法。不同站点可能把真实值保存在隐藏字段或框架状态中。

## 8. 文件上传与跨系统路径

先确认 `input[type=file]` 是否存在，以及：

```javascript
[...document.querySelectorAll('input[type=file]')].map(el => ({
  id: el.id,
  multiple: el.multiple,
  accept: el.accept
}))
```

如果使用 `DOM.setFileInputFiles`，文件路径由浏览器进程解析。因此 Windows Chrome 需要 Windows 可访问路径，例如：

```text
C:\Users\Akira\Downloads\evidence.zip
```

不是：

```text
/home/Akira/Downloads/evidence.zip
```

如果页面只允许上传一个文件，而凭证有多个，优先按主办方要求打包，不要尝试多次覆盖同一个单文件上传框。

## 9. 文件按时间定位

当用户只记得“几个文件挨得比较近”时，可以先按修改时间列出下载目录，再由文件名、时间和大小交叉确认。

PowerShell 示例：

```powershell
Get-ChildItem "$env:USERPROFILE\Downloads" |
  Sort-Object LastWriteTime -Descending |
  Select-Object LastWriteTime, Length, Name
```

不要只凭“最近的 PDF”自动上传，尤其在报销、合同、身份材料等场景。至少核对文件名和时间，必要时让用户确认。

## 10. 表单完成后的机器校验

最终检查可以返回一组结构化状态，例如：

```javascript
({
  name: document.querySelector('#q1')?.value,
  outboundAmount: document.querySelector('#q5')?.value,
  returnAmount: document.querySelector('#q9')?.value,
  cityTransport: document.querySelector('input[name="q11"]:checked')?.value,
  uploadMessage: document.querySelector('.uploadmsg')?.innerText || '',
  href: location.href
})
```

实际字段名必须来自当前页面勘察结果。

## 11. 事故预防

自动填写阶段不要执行以下行为：

```text
点击“提交”按钮
调用 form.submit()
调用站点自定义提交函数
在提交按钮获得焦点时发送 Enter
为了测试流程而真的提交一次再回退
```

如果用户要求“先不要提交”，最可靠的验收证据是：关键字段值已经填好、页面 URL 仍是填写页、提交按钮未触发、用户能在可视化 Chrome 中直接检查。

## 12. 本次问卷星实践得到的经验

在问卷星类动态问卷中，页面初始只显示顶层问题；选择“有”后，后续日期、交通工具、金额和发票号才会显示。实际操作应先点击上游单选，再读取新出现的 DOM。

上传控件的视觉文案可能显示“选择文件”，但真正约束需要结合 `input[type=file]` 属性和页面错误提示判断。本次页面在尝试多文件时明确提示“上传文件数量不能超过1个”，因此自动化应停止覆盖上传区，改由用户整理单一凭证包或手动上传。

对于“1,064 元是两个人一起买、本人只报销 532 元”这类情况，表单中的报销金额必须使用本人应报销金额，而不是支付记录中的整单金额。原始支付记录、个人车票金额和说明文件应三者一致。
