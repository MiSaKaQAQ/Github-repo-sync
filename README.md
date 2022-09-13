# Github-repo-sync
## 为什么要写这个工具
有的时候有些repo有时候会被DMCA takedown(比如说一些音乐视频下载工具),这个工具可以将储存库的代码及release同步到本地，防止一些软件在被DMCA takedown时删除了部分功能和代码

## 特点
- 操作简单
- 一键同步，易于使用
- GitHub API使用条件请求
- 支持自定义同步的内容
- 支持自定义保存的目录结构
- ……

## 如何使用
- `git clone xxx`
- 安装依赖
- `python main.py`
- 设置并开始使用

## 如何登录GitHub账户
**请务必登录GitHub账户因为不登陆单个IP GitHub API限制每小时仅60个请求，容易触发Rate Limit**
你的用户名和personal access token都会保存在同目录下的`config.json`中所以请不要将`config.json`分享给他人，一面你的账户被盗用，在反馈提交Issue时请删除里面的token。
###### 1.创建personal access token
步骤:
- 右上角头像 > Settings > Developer settings > Personal access tokens > Generate new token
- Note可以随便填，勾选下方复选框`read:user`，点击`Generate token`
- 之后复制出现的密匙，注意这个密匙**仅显示一次**请务必保存好

注意事项:
- 在获取token时请将`Expiration`设置为`No expiration`以防止token过期
- 请务必至少给予token`read:user`权限以便验证token是否正确
- 详细步骤见[GitHub Docs](https://docs.github.com/cn/authentication/keeping-your-account-and-data-secure/creating-a-personal-access-token#creating-a-token)

###### 2.登录
步骤
- `python main.py`运行程序
- 输入`1`选择登录
- 输入你的用户名和token
- 如果没有错误你应该再回到最初的页面时可以看到选项1变为`1: 重新登录(已登录: YOUR USERNAME)`

## GitHub无法访问/访问速度慢怎么办
你可以在`6: 设置`中配置GitHub镜像,设置是否启用ssl vertify，Releases下载间隔等，配置界面有详细说明。

## 如何更改储存位置
在`6: 设置`中更改

## 如何更改一个仓库的同步设置
在`4: 修改储存库同步设置`中更改