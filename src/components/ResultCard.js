export default function ResultCard({ title, content }) {
  return (
    <div className="bg-slate-800 p-6 rounded-xl shadow-lg hover:shadow-cyan-500/20 transition">
      <h3 className="text-2xl font-bold mb-3 text-cyan-400">
        {title}
      </h3>
      <p className="text-gray-300 leading-relaxed">
        {content}
      </p>
    </div>
  );
}
