"""金融配置服务模块"""
import json
import logging
from pathlib import Path
from typing import List, Dict, Optional
from pydantic import BaseModel

logger = logging.getLogger(__name__)

class StockConfig(BaseModel):
    symbol: str
    name: str
    type: str = "watching"  # holding or watching
    target_buy_price: float = 0.0
    target_sell_price: float = 0.0
    cost_price: float = 0.0
    shares: int = 0

class IndexConfig(BaseModel):
    symbol: str
    name: str

class FinanceService:
    """金融配置服务"""
    
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.stocks_file = self.data_dir / "stocks.json"
        self.indices_file = self.data_dir / "indices.json"
        self._ensure_files()
        
    def _ensure_files(self):
        """确保配置文件存在"""
        if not self.stocks_file.exists():
            self.save_stocks([])
        
        if not self.indices_file.exists():
            # 默认指数配置
            default_indices = [
                {'symbol': '000001.SS', 'name': '上证指数'},
                {'symbol': '399001.SZ', 'name': '深证成指'},
                {'symbol': '^IXIC', 'name': '纳斯达克'},
                {'symbol': '^DJI', 'name': '道琼斯'},
                {'symbol': '^HSI', 'name': '恒生指数'},
                {'symbol': '^VIX', 'name': 'VIX恐慌'},
                {'symbol': 'GC=F', 'name': '黄金'},
                {'symbol': 'BTC-USD', 'name': 'BTC'},
                {'symbol': 'ETH-USD', 'name': 'ETH'}
            ]
            self.save_indices(default_indices)
            
    def get_stocks(self) -> List[StockConfig]:
        """获取股票配置列表"""
        try:
            with open(self.stocks_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return [StockConfig(**item) for item in data]
        except Exception as e:
            logger.error(f"Error loading stocks config: {e}")
            return []
            
    def save_stocks(self, stocks: List[Dict]):
        """保存股票配置列表"""
        try:
            if not isinstance(stocks, list):
                raise ValueError("Stocks data must be a list")
                
            with open(self.stocks_file, 'w', encoding='utf-8') as f:
                json.dump(stocks, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Error saving stocks config: {e}")
            raise e
            
    def add_stock(self, stock: StockConfig):
        """添加股票"""
        stocks = self.get_stocks()
        for s in stocks:
            if s.symbol == stock.symbol:
                raise ValueError(f"Stock {stock.symbol} already exists")
        
        stocks.append(stock)
        self.save_stocks([s.dict() for s in stocks])
        
    def update_stock(self, symbol: str, stock_data: Dict):
        """更新股票"""
        stocks = self.get_stocks()
        found = False
        new_stocks = []
        
        for s in stocks:
            if s.symbol == symbol:
                updated_data = s.dict()
                updated_data.update(stock_data)
                new_stocks.append(StockConfig(**updated_data))
                found = True
            else:
                new_stocks.append(s)
                
        if not found:
            raise ValueError(f"Stock {symbol} not found")
            
        self.save_stocks([s.dict() for s in new_stocks])
        
    def delete_stock(self, symbol: str):
        """删除股票"""
        stocks = self.get_stocks()
        new_stocks = [s for s in stocks if s.symbol != symbol]
        self.save_stocks([s.dict() for s in new_stocks])

    # --- Indices Management ---

    def get_indices(self) -> List[IndexConfig]:
        """获取指数配置列表"""
        try:
            with open(self.indices_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return [IndexConfig(**item) for item in data]
        except Exception as e:
            logger.error(f"Error loading indices config: {e}")
            return []

    def save_indices(self, indices: List[Dict]):
        """保存指数配置列表"""
        try:
            if not isinstance(indices, list):
                raise ValueError("Indices data must be a list")
            
            with open(self.indices_file, 'w', encoding='utf-8') as f:
                json.dump(indices, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Error saving indices config: {e}")
            raise e

    def add_index(self, index: IndexConfig):
        """添加指数"""
        indices = self.get_indices()
        for i in indices:
            if i.symbol == index.symbol:
                raise ValueError(f"Index {index.symbol} already exists")
        
        indices.append(index)
        self.save_indices([i.dict() for i in indices])

    def delete_index(self, symbol: str):
        """删除指数"""
        indices = self.get_indices()
        new_indices = [i for i in indices if i.symbol != symbol]
        self.save_indices([i.dict() for i in new_indices])

# 全局实例工厂
def get_finance_service(config_dir: Path) -> FinanceService:
    return FinanceService(config_dir)
