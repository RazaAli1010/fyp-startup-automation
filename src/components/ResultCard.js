export default function ResultCard({ title, children }) {
  return (
    <div className="relative group">
      {/* Glow effect */}
      <div className="absolute -inset-0.5 bg-gradient-to-r from-emerald-500/20 via-blue-500/20 to-indigo-500/20 rounded-2xl blur opacity-0 group-hover:opacity-100 transition duration-500"></div>
      
      {/* Card content */}
      <div className="relative bg-gradient-to-br from-white/10 to-white/5 backdrop-blur-lg p-8 rounded-2xl border border-white/20 shadow-2xl hover:border-emerald-500/30 transition-all duration-300">
        {/* Title with gradient accent */}
        <div className="flex items-center gap-3 mb-6">
          <div className="h-8 w-1 bg-gradient-to-b from-emerald-400 to-blue-400 rounded-full"></div>
          <h3 className="text-2xl font-bold bg-gradient-to-r from-emerald-400 to-blue-400 bg-clip-text text-transparent">
            {title}
          </h3>
        </div>
        
        {/* Content */}
        <div className="text-gray-200 leading-relaxed space-y-3">
          {children}
        </div>

        {/* Decorative corner accent */}
        <div className="absolute top-0 right-0 w-20 h-20 bg-gradient-to-br from-emerald-500/10 to-transparent rounded-bl-full"></div>
      </div>
    </div>
  );
}