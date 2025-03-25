import './globals.css';
import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import { Navbar } from '@/components/Navbar';
import { AuthInitializer } from './AuthInitializer';

// 设置字体
const inter = Inter({ subsets: ['latin'] });

// 设置元数据
export const metadata: Metadata = {
  title: '音频分割工具',
  description: '一个简单易用的音频分割和转写工具，可以将长音频文件分割成小段',
};

// 应用布局组件
export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="zh-CN">
      <body className={inter.className}>
        <AuthInitializer />
        <div className="min-h-screen bg-gray-50">
          <Navbar />
          <main className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
            {children}
          </main>
          <footer className="bg-white border-t border-gray-200 py-4">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
              <p className="text-center text-gray-500 text-sm">
                © {new Date().getFullYear()} 音频分割工具 - 保留所有权利
              </p>
            </div>
          </footer>
        </div>
      </body>
    </html>
  );
} 