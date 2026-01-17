"use client";

export default function Navbar() {
  return (
    <nav className="fixed top-0 left-0 right-0 z-50 bg-gray-900/80 backdrop-blur-md border-b border-white/10">
      <div className="flex justify-between items-center px-10 py-4 max-w-7xl mx-auto">
        <a href="/" className="group flex items-center gap-2">
          <div className="relative">
            <div className="absolute inset-0 bg-gradient-to-r from-emerald-500 to-blue-500 rounded-lg blur opacity-50 group-hover:opacity-75 transition duration-300"></div>
            <div className="relative bg-gradient-to-r from-emerald-500 to-blue-500 p-2 rounded-lg">
              <span className="text-xl">🚀</span>
            </div>
          </div>
          <span className="text-2xl font-bold bg-gradient-to-r from-emerald-400 to-blue-400 bg-clip-text text-transparent">
            StartupAgent
          </span>
        </a>

        <div className="flex items-center space-x-6">
          <a 
            href="/" 
            className="text-gray-300 hover:text-emerald-400 transition-colors duration-200 font-medium relative group"
          >
            Home
            <span className="absolute bottom-0 left-0 w-0 h-0.5 bg-gradient-to-r from-emerald-400 to-blue-400 group-hover:w-full transition-all duration-300"></span>
          </a>
          
          <div className="relative group">
            <div className="absolute -inset-0.5 bg-gradient-to-r from-emerald-500 to-blue-500 rounded-lg blur opacity-50 group-hover:opacity-75 transition duration-300"></div>
            <a
              href="/validate"
              className="relative bg-gradient-to-r from-emerald-500 to-emerald-400 px-6 py-2.5 rounded-lg text-black font-semibold hover:shadow-lg hover:scale-105 transition-all duration-200 inline-block"
            >
              Validate Your Idea
            </a>
          </div>
        </div>
      </div>

      <style jsx>{`
        nav::before {
          content: '';
          position: absolute;
          top: 0;
          left: 0;
          right: 0;
          height: 1px;
          background: linear-gradient(
            90deg,
            transparent,
            rgba(16, 185, 129, 0.3) 20%,
            rgba(59, 130, 246, 0.3) 50%,
            rgba(99, 102, 241, 0.3) 80%,
            transparent
          );
        }
      `}</style>
    </nav>
  );
}