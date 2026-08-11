# 用户授权访问

当 WebFetch / HTTP / exact-work resolution search 已定位目标页面，但全文需要用户已有的机构、订阅或出版社权限时，把浏览器部分交给当前环境可用的浏览器访问能力。

交接目标只有两个：

1. 让用户在可见、可复用的授权环境中完成必要登录；
2. 让浏览器能力返回真正的全文 `Artifact Request`，而不是替本 Skill 把文件下载到浏览器默认 Downloads 目录。

浏览器能力负责自身的能力发现、用户授权、Profile 复用、登录、二次认证和动态页面操作。本 Skill 不复制这些规则。

用户完成登录后重新解析目标论文页面。若拿到资源请求，状态变为 `ARTIFACT_REQUEST_READY` 并进入 `../fetch/ROUTER.md`；若当前环境没有可用浏览器能力，返回 `MANUAL_ACQUISITION_REQUIRED`。
