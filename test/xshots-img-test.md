# 图片解析测试

这是一篇用来验证图片解析的笔记。下面应该出现一张从 vault 里按文件名找到的图。

![[diagram.png]]

上面那张图用的是 Obsidian 的 `![[diagram.png]]` 内部链接写法，脚本会去 vault 里按 basename 递归找到 `sub/diagram.png`。

## 标准 markdown 图

下面这张用标准 markdown 写法，带 alt 文本：

![一张配图](diagram.png)

正文继续。图片不应该被腰斩，分页时整张图会被推到下一页顶部。
