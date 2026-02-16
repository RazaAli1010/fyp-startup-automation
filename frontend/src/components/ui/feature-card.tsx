interface FeatureCardProps {
  icon: React.ReactNode;
  title: string;
  description: string;
}

export function FeatureCard({ icon, title, description }: FeatureCardProps) {
  return (
    <div className="gradient-border group relative rounded-2xl bg-[#0f172a] p-6 transition-all duration-300 hover:bg-[#131c31] hover:scale-[1.02]">
      <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-500/20 to-purple-500/20 text-2xl transition-transform duration-300 group-hover:scale-110">
        {icon}
      </div>
      <h3 className="mb-2 text-lg font-semibold text-slate-100">{title}</h3>
      <p className="text-sm leading-relaxed text-slate-400">{description}</p>
    </div>
  );
}
