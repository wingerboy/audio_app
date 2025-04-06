/**
 * 将秒数格式化为 hh:mm:ss 或 mm:ss 的格式
 * @param seconds 秒数
 * @returns 格式化后的时间字符串
 */
export function formatTime(seconds: number): string {
  if (isNaN(seconds) || seconds < 0) return '00:00';
  
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  
  return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
}

/**
 * 将 "mm:ss" 或 "hh:mm:ss" 格式的字符串转换为秒数
 * @param timeString 时间字符串
 * @returns 秒数
 */
export function timeStringToSeconds(timeString: string): number {
  if (!timeString) return 0;
  
  const parts = timeString.split(':').map(part => parseInt(part, 10));
  
  if (parts.length === 3) {
    // hh:mm:ss 格式
    return parts[0] * 3600 + parts[1] * 60 + parts[2];
  } else if (parts.length === 2) {
    // mm:ss 格式
    return parts[0] * 60 + parts[1];
  }
  
  return 0;
} 