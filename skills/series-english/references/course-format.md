# 课程格式 v1

所有字段使用 UTF-8。`seriesId` 是固定的剧目标识，同一剧所有课程保持一致；季和集为正整数。课程 ID 由 CLI 生成为 `seriesId-s01e01`。`source` 与 prepare 时完全相同。`sourceLine` 是 evidence 的行 ID，不是原字幕文件的物理行号。

```json
{
  "schemaVersion": 1,
  "seriesId": "my-series",
  "series": "My Series",
  "season": 1,
  "episode": 1,
  "title": "本集标题",
  "language": "中文",
  "source": "用户提供的字幕",
  "words": [{
    "term": "figure out",
    "meaning": "弄清楚；想出",
    "ipa": "ˈfɪɡjər aʊt",
    "sentence": "We need to figure out a better route.",
    "translation": "我们需要想出一条更好的路线。",
    "tip": "强调通过思考找到答案。",
    "sourceLine": 2,
    "sourceForm": "figure out"
  }]
}
```

`sourceForm` 必须是对应来源行中实际出现的短表达（不超过 12 个词）。例如 `term` 为 `figure out`，来源是 `figured it out` 时，填写实际的 `sourceForm`。人工审校需确认两者为同一表达，结构校验无法推断这一点。

跨集匹配由小写、空格、常见标点规范化后的 `term` 决定。因此用同一词典原形命名，别一集写 `picks up`，另一集写 `pick up`。不同语境的词义按每集分别解释；“复习词”仅代表表达形式已收录，不保证词义相同。

`add` 仅复制白名单展示字段，剥离证据与来源句，重算 `key`、`review`、`firstEpisode`。不得手工篡改这些生成字段。公开课程仍需用户确认其内容和来源的使用权。

参考可执行示例：`assets/demo/lesson-01.json`，对应 `assets/demo/dialogue.srt`，全部为原创。
