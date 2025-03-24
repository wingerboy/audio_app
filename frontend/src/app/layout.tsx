import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';

// 设置字体
const inter = Inter({ subsets: ['latin'] });

// 设置元数据
export const metadata: Metadata = {
  title: '智能音频分割工具',
  description: '使用AI技术智能分割音频和视频文件',
};

// 应用布局组件
export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="zh-CN">
      <body className={inter.className}>
        <div className="min-h-screen py-10 px-4 sm:px-6 lg:px-8">
          <header className="max-w-7xl mx-auto mb-8">
            <div className="flex items-center justify-between">
              <h1 className="text-3xl font-bold text-primary-600">
                智能音频分割工具
              </h1>
              <div className="text-sm text-gray-500">
                AI驱动的音频处理解决方案
              </div>
            </div>
          </header>
          
          <main className="max-w-7xl mx-auto">
            {children}
          </main>
          
          <footer className="max-w-7xl mx-auto mt-16 pt-8 border-t border-gray-200 text-center text-sm text-gray-500">
            <p>© {new Date().getFullYear()} 智能音频分割工具 - 使用Whisper AI技术提供支持</p>
          </footer>
        </div>
      </body>
    </html>
  );
} 