export function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center py-24 animate-fade-in">
      <div className="w-14 h-14 rounded-2xl bg-[#171717] flex items-center justify-center mb-6">
        <span className="text-2xl font-semibold text-white">L</span>
      </div>

      <h2 className="text-xl font-semibold mb-2 text-[#171717]">
        你好，我是 Leon
      </h2>
      <p className="text-sm mb-10 text-[#737373]">
        你的通用数字员工，随时准备为你工作
      </p>

      <div className="grid grid-cols-2 gap-3 max-w-md w-full">
        {[
          { title: "文件操作", desc: "读取、编辑、搜索项目文件" },
          { title: "代码探索", desc: "理解代码结构和实现逻辑" },
          { title: "命令执行", desc: "运行终端命令、Git 操作" },
          { title: "信息检索", desc: "搜索文档和网络资源" },
        ].map((item, i) => (
          <div
            key={item.title}
            className="px-4 py-3.5 rounded-xl border border-[#e5e5e5] hover:border-[#d4d4d4] hover:shadow-sm transition-all cursor-default animate-fade-in"
            style={{ animationDelay: `${i * 0.06}s`, opacity: 0 }}
          >
            <div className="text-sm font-medium mb-0.5 text-[#171717]">{item.title}</div>
            <div className="text-xs text-[#737373]">{item.desc}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
