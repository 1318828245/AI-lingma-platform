export const STAGES = [
  { key: "parse", title: "解析", hint: "理解你的需求" },
  { key: "plan", title: "规划", hint: "安排要做哪些改动" },
  { key: "generate", title: "生成", hint: "正在写代码" },
  { key: "build", title: "构建", hint: "检查能否正常运行" },
  { key: "repair", title: "修复", hint: "修正发现的问题" },
  { key: "done", title: "完成", hint: "已经可以预览了" },
];

export function stageInfo(key: string) {
  return (
    STAGES.find((s) => s.key === key) ?? { key, title: key, hint: "" }
  );
}
