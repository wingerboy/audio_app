import datetime
from decimal import Decimal, ROUND_DOWN

class BalanceUtils:
    """余额工具类"""
    
    @staticmethod
    def format_money(amount: Decimal) -> str:
        """格式化金额为字符串"""
        return f"¥{float(amount):.2f}"
    
    @staticmethod
    def round_down(amount: Decimal, places: int = 2) -> Decimal:
        """向下取整金额"""
        return amount.quantize(Decimal('0.1') ** places, rounding=ROUND_DOWN)
    
    @staticmethod
    def get_current_month_range() -> tuple:
        """获取当前月份的开始和结束日期"""
        now = datetime.datetime.now()
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # 获取下个月的第一天
        if now.month == 12:
            end = now.replace(year=now.year + 1, month=1, day=1, 
                              hour=0, minute=0, second=0, microsecond=0)
        else:
            end = now.replace(month=now.month + 1, day=1, 
                               hour=0, minute=0, second=0, microsecond=0)
        
        return start, end
    
    @staticmethod
    def get_transaction_description(api_type: str, model_size: str = None) -> str:
        """生成交易描述"""
        description = f"使用{api_type}服务"
        
        if model_size:
            description += f" ({model_size})"
            
        return description 