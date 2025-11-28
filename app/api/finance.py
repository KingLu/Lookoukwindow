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

class StockPoint(BaseModel):
    t: str
    v: float

class StockData(BaseModel):
    symbol: str
    name: str
    price: float
    change: float
    change_percent: float
    history_1d: List[StockPoint]
    history_1y: List[StockPoint]
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
    """获取单个股票详情及历史趋势 (当日+1年)"""
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
            
        # --- 获取当日分时数据 (1d, 5m) ---
        history_1d_points = []
        try:
            # interval='5m' 比较适合日内趋势
            hist_1d = ticker.history(period="1d", interval="5m")
            if not hist_1d.empty:
                # 格式化: t=HH:MM, v=Close
                # index 是 datetime
                for idx, row in hist_1d.iterrows():
                    # 使用 strftime 格式化时间
                    t_str = idx.strftime("%H:%M")
                    val = row['Close']
                    if val == val: # not NaN
                        history_1d_points.append(StockPoint(t=t_str, v=round(val, 2)))
        except Exception as e:
            logger.warning(f"Failed to fetch 1d history for {symbol}: {e}")

        # 如果当日没数据(比如盘前)，尝试拿最近一次交易日的数据
        if not history_1d_points:
            try:
                 hist_5d = ticker.history(period="5d", interval="15m")
                 if not hist_5d.empty:
                    # 取最后一天的数据
                    last_date = hist_5d.index[-1].date()
                    last_day_data = hist_5d[hist_5d.index.date == last_date]
                    for idx, row in last_day_data.iterrows():
                        t_str = idx.strftime("%H:%M")
                        val = row['Close']
                        if val == val:
                             history_1d_points.append(StockPoint(t=t_str, v=round(val, 2)))
            except Exception:
                pass


        # --- 获取1年日线数据 (1y, 1d) ---
        history_1y_points = []
        try:
            hist_1y = ticker.history(period="1y", interval="1d")
            if not hist_1y.empty:
                 # 降采样，避免点太多
                 # 一年约250个交易日，取50个点左右
                 data_list = hist_1y['Close'].dropna().tolist()
                 idx_list = hist_1y.index[hist_1y['Close'].notna()].tolist()
                 
                 total_len = len(data_list)
                 step = max(1, total_len // 50)
                 
                 for i in range(0, total_len, step):
                     val = data_list[i]
                     dt = idx_list[i]
                     t_str = dt.strftime("%Y-%m") # 显示年月即可，或者 %m-%d
                     history_1y_points.append(StockPoint(t=t_str, v=round(val, 2)))
                     
                 # 确保包含最后一个点(最新价)
                 if total_len > 0 and (total_len - 1) % step != 0:
                     val = data_list[-1]
                     dt = idx_list[-1]
                     t_str = dt.strftime("%Y-%m")
                     history_1y_points.append(StockPoint(t=t_str, v=round(val, 2)))

        except Exception as e:
            logger.warning(f"Failed to fetch 1y history for {symbol}: {e}")

        return {
            "symbol": symbol,
            "name": name or symbol,
            "price": round(price or 0.0, 2),
            "change": round(change, 2),
            "change_percent": round(change_percent, 2),
            "history_1d": history_1d_points,
            "history_1y": history_1y_points,
            "currency": currency
        }
    except Exception as e:
        logger.error(f"Error fetching stock {symbol}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch stock data: {str(e)}")

@router.get("/watchlist")
async def get_watchlist(config: Config = Depends(get_config)):
    """获取自选股列表配置"""
    return config.get('finance.stocks', [])

