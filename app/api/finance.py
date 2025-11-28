"""金融数据API路由"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict
import yfinance as yf
import asyncio
import logging
from datetime import datetime, timedelta

from ..core.config import Config

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/finance", tags=["finance"])

def get_config() -> Config:
    return Config()

class IndexData(BaseModel):
    symbol: str
    name: str
    price: float
    change: float
    change_percent: float

class StockData(BaseModel):
    symbol: str
    name: str
    price: float
    change: float
    change_percent: float
    history: List[float]  # 简化的历史数据用于绘图
    currency: str

@router.get("/indices", response_model=List[IndexData])
async def get_indices(config: Config = Depends(get_config)):
    """获取大盘指数数据"""
    indices_config = config.get('finance.indices', [])
    if not indices_config:
        return []
    
    # 构造 symbol 列表
    symbols = [item['symbol'] for item in indices_config]
    
    try:
        # yfinance 批量获取对象 (注意：这不会立即发起网络请求)
        tickers = yf.Tickers(' '.join(symbols))
        results = []
        
        for item in indices_config:
            symbol = item['symbol']
            name = item['name']
            try:
                # 访问 tickers.tickers[symbol] 获取单个 ticker 对象
                ticker = tickers.tickers[symbol]
                
                # 使用 fast_info 获取最新价格，这通常比 .info 快且稳定
                info = ticker.fast_info
                price = info.last_price
                prev_close = info.previous_close
                
                if price is not None and prev_close is not None:
                    change = price - prev_close
                    # 避免除以零
                    change_percent = (change / prev_close) * 100 if prev_close != 0 else 0.0
                    
                    results.append({
                        "symbol": symbol,
                        "name": name,
                        "price": round(price, 2),
                        "change": round(change, 2),
                        "change_percent": round(change_percent, 2)
                    })
                else:
                    # 数据不完整
                    results.append({
                        "symbol": symbol,
                        "name": name,
                        "price": 0.0,
                        "change": 0.0,
                        "change_percent": 0.0
                    })

            except Exception as e:
                logger.error(f"Error fetching index {symbol}: {e}")
                # 出错时返回零值，保证前端不崩
                results.append({
                    "symbol": symbol,
                    "name": name,
                    "price": 0.0,
                    "change": 0.0,
                    "change_percent": 0.0
                })
                
        return results
    except Exception as e:
        logger.error(f"Bulk fetch error: {e}")
        # 如果整体初始化失败，返回空列表或抛出异常
        return []

@router.get("/stock/{symbol}", response_model=StockData)
async def get_stock(symbol: str, name: str = "", config: Config = Depends(get_config)):
    """获取单个股票详情及历史趋势"""
    try:
        ticker = yf.Ticker(symbol)
        
        # 获取实时价格
        info = ticker.fast_info
        price = info.last_price
        prev_close = info.previous_close
        currency = info.currency
        
        change = 0.0
        change_percent = 0.0
        if price is not None and prev_close is not None:
            change = price - prev_close
            change_percent = (change / prev_close) * 100 if prev_close != 0 else 0.0
            
        # 获取历史数据用于绘图
        # 优先尝试获取今天的分钟级数据
        try:
            hist = ticker.history(period="1d", interval="5m")
            if hist.empty:
                # 如果今天没数据（比如周末或盘前），获取最近5天的小时级数据
                hist = ticker.history(period="5d", interval="60m")
        except Exception:
             hist = ticker.history(period="5d", interval="1d")
            
        history_prices = []
        if not hist.empty:
            # 提取收盘价序列，处理 NaN
            history_prices = [x for x in hist['Close'].tolist() if x == x] # remove NaN
            
            # 简化数据点，避免前端渲染压力过大
            target_points = 50
            if len(history_prices) > target_points:
                step = len(history_prices) // target_points
                history_prices = history_prices[::step]
        
        # 如果还是没有数据，填充当前价格
        if not history_prices and price:
             history_prices = [price] * 10

        return {
            "symbol": symbol,
            "name": name or symbol,
            "price": round(price or 0.0, 2),
            "change": round(change, 2),
            "change_percent": round(change_percent, 2),
            "history": [round(p, 2) for p in history_prices],
            "currency": currency
        }
    except Exception as e:
        logger.error(f"Error fetching stock {symbol}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch stock data: {str(e)}")

@router.get("/watchlist")
async def get_watchlist(config: Config = Depends(get_config)):
    """获取自选股列表配置"""
    return config.get('finance.stocks', [])

