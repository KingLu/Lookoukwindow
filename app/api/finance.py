"""金融数据API路由"""
from fastapi import APIRouter, Depends, HTTPException, Body
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import yfinance as yf
import asyncio
import logging
from datetime import datetime, timedelta

from ..core.config import Config
from ..services.finance_service import get_finance_service, FinanceService, StockConfig, IndexConfig

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/finance", tags=["finance"])

def get_config() -> Config:
    return Config()

def get_service(config: Config = Depends(get_config)) -> FinanceService:
    return get_finance_service(config.data_dir)

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
    # 策略字段
    type: str
    target_buy_price: float
    target_sell_price: float
    cost_price: float
    shares: int
    holding_value: float = 0.0
    holding_gain: float = 0.0
    holding_gain_percent: float = 0.0
    # 历史数据
    history_3y: List[StockPoint]  # 3年周线
    ma_250: List[StockPoint]      # 年线(近似)
    currency: str
    # 新增字段
    year_high: float = 0.0
    year_low: float = 0.0
    volume: int = 0
    prev_close: float = 0.0
    analyst_target_price: Optional[float] = None
    # 财报日可能返回空，处理为可选
    earnings_date: Optional[str] = None

@router.get("/indices", response_model=List[IndexData])
async def get_indices(service: FinanceService = Depends(get_service)):
    """获取大盘指数数据"""
    # 从新服务获取配置
    indices_config = service.get_indices()
    if not indices_config:
        return []
    
    # 构造 symbol 列表
    symbols = [item.symbol for item in indices_config]
    
    try:
        # yfinance 批量获取对象
        tickers = yf.Tickers(' '.join(symbols))
        results = []
        
        for item in indices_config:
            symbol = item.symbol
            name = item.name
            try:
                # 访问 tickers.tickers[symbol] 获取单个 ticker 对象
                ticker = tickers.tickers[symbol]
                
                # 使用 fast_info 获取最新价格
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
        return []

@router.get("/indices/config", response_model=List[IndexConfig])
async def get_indices_config(service: FinanceService = Depends(get_service)):
    """获取指数配置列表"""
    return service.get_indices()

@router.post("/indices/config")
async def add_index_config(
    index: IndexConfig,
    service: FinanceService = Depends(get_service)
):
    """添加指数配置"""
    try:
        service.add_index(index)
        return {"status": "success"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/indices/config/{symbol}")
async def delete_index_config(
    symbol: str,
    service: FinanceService = Depends(get_service)
):
    """删除指数配置"""
    service.delete_index(symbol)
    return {"status": "success"}


@router.get("/stock/{symbol}", response_model=StockData)
async def get_stock(
    symbol: str, 
    service: FinanceService = Depends(get_service)
):
    """获取单个股票详情及历史趋势 (3年周线 + 策略信息)"""
    try:
        # 1. 获取本地配置
        stocks = service.get_stocks()
        stock_config = next((s for s in stocks if s.symbol == symbol), None)
        
        if not stock_config:
            # 临时兼容：如果没找到配置，用默认值
            stock_config = StockConfig(symbol=symbol, name=symbol)

        # 2. 获取 YFinance 数据
        ticker = yf.Ticker(symbol)
        
        # 获取实时价格及其他基础信息
        info = ticker.fast_info
        price = info.last_price
        prev_close = info.previous_close
        currency = info.currency
        
        # 扩展信息：52周高低、成交量
        year_high = info.year_high if info.year_high is not None else 0.0
        year_low = info.year_low if info.year_low is not None else 0.0
        volume = info.last_volume if info.last_volume is not None else 0
        
        # 获取分析师目标价（需要从 ticker.info 获取，不是 fast_info）
        # 注意：ticker.info 比 fast_info 慢，这里可以考虑缓存或者异步
        analyst_target = None
        try:
            # 只有需要的时候才去获取完整 info，因为比较慢
            # 如果只用 fast_info 拿不到目标价
            # 这里为了性能，可以做个权衡，先尝试用 fast_info (虽然大概率没有)
            # 必须用 info
            full_info = ticker.info 
            analyst_target = full_info.get('targetMeanPrice') or full_info.get('targetMedianPrice')
            if analyst_target:
                analyst_target = float(analyst_target)
        except Exception as e:
            logger.debug(f"Failed to fetch analyst target for {symbol}: {e}")
            
        # 财报日
        earnings_date_str = None
        try:
            cal = ticker.calendar
            if cal is not None:
                # 1. 处理 DataFrame (具有 empty 属性)
                if hasattr(cal, 'empty'):
                    if not cal.empty and 'Earnings Date' in cal:
                         dates = cal['Earnings Date']
                         if not dates.empty:
                             earnings_date_str = str(dates.iloc[0].date())
                
                # 2. 处理字典 (新版 yfinance 可能返回字典)
                elif isinstance(cal, dict):
                    earnings_dates = cal.get('Earnings Date')
                    if earnings_dates:
                         # 可能是列表
                         if isinstance(earnings_dates, list) and len(earnings_dates) > 0:
                             d = earnings_dates[0]
                             earnings_date_str = str(d.date()) if hasattr(d, 'date') else str(d)

        except Exception as e:
            logger.debug(f"Failed to fetch earnings calendar for {symbol}: {e}")

        
        change = 0.0
        change_percent = 0.0
        if price is not None and prev_close is not None:
            change = price - prev_close
            change_percent = (change / prev_close) * 100 if prev_close != 0 else 0.0
            
        # 3. 计算持仓信息
        current_price = price or 0.0
        holding_value = 0.0
        holding_gain = 0.0
        holding_gain_percent = 0.0
        
        if stock_config.shares > 0:
            holding_value = stock_config.shares * current_price
            cost_basis = stock_config.shares * stock_config.cost_price
            if cost_basis > 0:
                holding_gain = holding_value - cost_basis
                holding_gain_percent = (holding_gain / cost_basis) * 100

        # 4. 获取3年周线数据 (3y, 1wk) - 用于周期分析
        history_3y_points = []
        ma_250_points = [] # 实际上这里用 50周均线 近似 年线 (52周)
        
        try:
            # 获取3年数据，周线
            hist = ticker.history(period="3y", interval="1wk")
            
            if not hist.empty:
                # 计算 MA50 (50周均线 ≈ 年线)
                hist['MA50'] = hist['Close'].rolling(window=50).mean()
                
                # 降采样/格式化
                # 3年约150周，数据量适中，不需要强力降采样
                for idx, row in hist.iterrows():
                    val = row['Close']
                    ma = row['MA50']
                    if val == val: # not NaN
                        t_str = idx.strftime("%Y-%m")
                        history_3y_points.append(StockPoint(t=t_str, v=round(val, 2)))
                        
                        # 均线数据 (前面50周是NaN)
                        if ma == ma:
                            ma_250_points.append(StockPoint(t=t_str, v=round(ma, 2)))
                        else:
                             ma_250_points.append(StockPoint(t=t_str, v=0)) # 占位

        except Exception as e:
            logger.warning(f"Failed to fetch history for {symbol}: {e}")

        return {
            "symbol": symbol,
            "name": stock_config.name,
            "price": round(price or 0.0, 2),
            "change": round(change, 2),
            "change_percent": round(change_percent, 2),
            # 策略
            "type": stock_config.type,
            "target_buy_price": stock_config.target_buy_price,
            "target_sell_price": stock_config.target_sell_price,
            "cost_price": stock_config.cost_price,
            "shares": stock_config.shares,
            "holding_value": round(holding_value, 2),
            "holding_gain": round(holding_gain, 2),
            "holding_gain_percent": round(holding_gain_percent, 2),
            # 图表
            "history_3y": history_3y_points,
            "ma_250": ma_250_points,
            "currency": currency,
            # 新增扩展数据
            "year_high": round(year_high, 2),
            "year_low": round(year_low, 2),
            "volume": volume,
            "prev_close": round(prev_close or 0.0, 2),
            "analyst_target_price": round(analyst_target, 2) if analyst_target else None,
            "earnings_date": earnings_date_str
        }
    except Exception as e:
        logger.error(f"Error fetching stock {symbol}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch stock data: {str(e)}")

@router.get("/config", response_model=List[StockConfig])
async def get_stock_config(service: FinanceService = Depends(get_service)):
    """获取股票配置列表"""
    return service.get_stocks()

@router.post("/config")
async def save_stock_config(
    stock: StockConfig,
    service: FinanceService = Depends(get_service)
):
    """添加股票配置"""
    try:
        service.add_stock(stock)
        return {"status": "success"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.put("/config/{symbol}")
async def update_stock_config(
    symbol: str,
    stock: StockConfig,
    service: FinanceService = Depends(get_service)
):
    """更新股票配置"""
    try:
        # 确保 symbol 一致
        if stock.symbol != symbol:
             raise HTTPException(status_code=400, detail="Symbol mismatch")
        service.update_stock(symbol, stock.dict())
        return {"status": "success"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.delete("/config/{symbol}")
async def delete_stock_config(
    symbol: str,
    service: FinanceService = Depends(get_service)
):
    """删除股票配置"""
    service.delete_stock(symbol)
    return {"status": "success"}

@router.get("/watchlist")
async def get_watchlist_legacy(service: FinanceService = Depends(get_service)):
    """获取自选股列表 (兼容旧接口，实际返回新的配置结构)"""
    # 以前返回简单的 dict list，现在返回完整的对象
    stocks = service.get_stocks()
    return [s.dict() for s in stocks]
