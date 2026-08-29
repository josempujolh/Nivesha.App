import streamlit as st
import yfinance as yf
import pandas as pd
import json
import requests
import os
import textwrap
import random
import hashlib
import secrets
from supabase import create_client, Client

# ============================================
# CONFIGURATION
# ============================================
st.set_page_config(page_title="Nivesha", page_icon="logo.png", layout="wide")
WATCHLIST_FILE = "my_watchlist.json"

# Leer claves de los secretos
AV_KEY = st.secrets["AV_KEY"]
AV_URL = "https://www.alphavantage.co/query"

# Conexión a Supabase
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

if "lang" not in st.session_state:
    st.session_state.lang = "en"

# Avatar options (Simplificado)
AVATARS = ["👨", "👩"]

# ============================================
# DATABASE & AUTH SYSTEM (Supabase)
# ============================================
def hash_password(password):
    salt = secrets.token_hex(16)
    hash_obj = hashlib.sha256((password + salt).encode())
    return f"{salt}${hash_obj.hexdigest()}"

def verify_password(password, hashed_password):
    salt, hashed = hashed_password.split('$')
    hash_obj = hashlib.sha256((password + salt).encode())
    return hash_obj.hexdigest() == hashed

def register_user(email, password, first_name, last_name, avatar):
    try:
        hashed_pw = hash_password(password)
        supabase.table("users").insert({
            "email": email, 
            "password": hashed_pw, 
            "first_name": first_name, 
            "last_name": last_name, 
            "avatar": avatar
        }).execute()
        return True
    except Exception as e:
        # Si el correo ya existe, Supabase da error de duplicado
        if "duplicate" in str(e).lower() or "unique" in str(e).lower():
            return False
        return False

def authenticate_user(email, password):
    try:
        response = supabase.table("users").select("id, password, is_premium, first_name, last_name, avatar").eq("email", email).execute()
        if not response.data:
            return None
        
        user = response.data[0] # Tomar el primer resultado
        if verify_password(password, user["password"]):
            return {
                "id": user["id"], "email": email, "is_premium": bool(user["is_premium"]),
                "first_name": user["first_name"], "last_name": user["last_name"], "avatar": user["avatar"]
            }
        return None
    except:
        return None



if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_data = None

if "selected_avatar" not in st.session_state:
    st.session_state.selected_avatar = "🧑"

# ============================================
# TRADUCCIONES
# ============================================
T = {
    "app_subtitle": {"en": "Is it a good investment? Let's find out in plain English.", "es": "¿Es una buena inversión? Descubrámoslo en palabras simples."},
    "watchlist_header": {"en": "⭐ My Watchlist", "es": "⭐ Mi Lista de Seguimiento"},
    "add_ticker": {"en": "Add Ticker", "es": "Añadir Ticker"},
    "placeholder_ticker": {"en": "e.g. TSLA", "es": "ej. TSLA"},
    "add_button": {"en": "➕ Add to List", "es": "➕ Añadir a la Lista"},
    "added_msg": {"en": "Added {ticker}!", "es": "¡Se añadió {ticker}!"},
    "already_in_list": {"en": "{ticker} is already in your list.", "es": "{ticker} ya está en tu lista."},
    "empty_list": {"en": "Your list is empty.", "es": "Tu lista está vacía."},
    "clear_list": {"en": "🗑️ Clear Entire List", "es": "🗑️ Borrar Toda la Lista"},
    "tab_single": {"en": "🔍 Single Stock Check", "es": "🔍 Análisis Individual"},
    "tab_vs": {"en": "⚔️ Versus Mode", "es": "⚔️ Modo Versus"},
    "enter_ticker": {"en": "Enter Stock Ticker", "es": "Ingresa el Ticker"},
    "check_stock": {"en": "Check Stock", "es": "Analizar Acción"},
    "current_price": {"en": "Current Price", "es": "Precio Actual"},
    "health_score": {"en": "Investment Health Score", "es": "Salud de Inversión"},
    "sector": {"en": "Sector", "es": "Sector"},
    "unknown_sector": {"en": "Unknown Sector", "es": "Sector Desconocido"},
    "price_history": {"en": "📈 View Stock Price History (Past 2 Years)", "es": "📈 Ver Historial de Precio (Últimos 2 Años)"},
    "load_history_err": {"en": "Could not load price history.", "es": "No se pudo cargar el historial de precios."},
    "geek_mode": {"en": "🤓 Geek Mode: View exact 13 financial ratios", "es": "🤓 Modo Experto: Ver los 13 ratios financieros exactos"},
    "ratio": {"en": "Ratio", "es": "Ratio"},
    "value": {"en": "Value", "es": "Valor"},
    "unit": {"en": "Unit", "es": "Unidad"},
    "what_to_see": {"en": "What You Want To See", "es": "Lo Que Quieres Ver"},
    "vs_intro": {"en": "Which stock is better? Let them fight. 🥊", "es": "¿Qué acción es mejor? Que luchen. 🥊"},
    "stock_a": {"en": "Stock A", "es": "Acción A"},
    "stock_b": {"en": "Stock B", "es": "Acción B"},
    "fight_btn": {"en": "⚔️ FIGHT!", "es": "⚔️ ¡LUCHAR!"},
    "wins_by": {"en": "🏆 {winner} wins by {diff} points!", "es": "🏆 ¡{winner} gana por {diff} puntos!"},
    "tie": {"en": "🤝 It's a perfect tie!", "es": "🤝 ¡Es un empate perfecto!"},
    "err_data": {"en": "Could not find data for {ticker}. Did you type the ticker correctly?", "es": "No se encontraron datos para {ticker}. ¿Escribiste el ticker correctamente?"},
    "err_one_or_both": {"en": "Could not analyze one or both stocks.", "es": "No se pudo analizar una o ambas acciones."},
    "rate_limit": {"en": "🛑 Daily limit reached! You used your 5 free checks for today. They reset at midnight US Eastern Time.", "es": "🛑 ¡Límite diario alcanzado! Usaste tus 5 cheques gratis de hoy. Se reinician a la medianoche (Hora del Este de EE.UU.)."},
    "debug_err": {"en": "Debug Error: {err}", "es": "Error de Depuración: {err}"},
    "no_data_av": {"en": "Could not find data for this stock.", "es": "No se pudieron encontrar datos para esta acción."},
    "na": {"en": "N/A", "es": "N/D"},
    "safety": {"en": "SAFETY", "es": "SEGURIDAD"},
    "profitability": {"en": "PROFITABILITY", "es": "RENTABILIDAD"},
    "price_value": {"en": "PRICE VALUE", "es": "VALOR DE PRECIO"},
    "logout": {"en": "🚪 Logout", "es": "🚪 Cerrar Sesión"},
    
    # Auth
    "auth_title": {"en": "Welcome to Nivesha", "es": "Bienvenido a Nivesha"},
    "auth_subtitle": {"en": "Log in or create an account to continue.", "es": "Inicia sesión o crea una cuenta para continuar."},
    "login_tab": {"en": "🔐 Login", "es": "🔐 Iniciar Sesión"},
    "register_tab": {"en": "📝 Register", "es": "📝 Registrarse"},
    "email": {"en": "Email", "es": "Correo Electrónico"},
    "password": {"en": "Password", "es": "Contraseña"},
    "first_name": {"en": "First Name", "es": "Nombre"},
    "last_name": {"en": "Last Name", "es": "Apellido"},
    "login_btn": {"en": "Login", "es": "Entrar"},
    "register_btn": {"en": "Create Account", "es": "Crear Cuenta"},
    "err_user_exists": {"en": "This email is already registered.", "es": "Este correo ya está registrado."},
    "err_invalid_creds": {"en": "Invalid email or password.", "es": "Correo o contraseña incorrectos."},
    "reg_success": {"en": "Account created successfully! Please log in.", "es": "¡Cuenta creada exitosamente! Por favor inicia sesión."},
    "choose_avatar": {"en": "Choose your Avatar", "es": "Elige tu Avatar"},
    
    # Free Version Notice
    "free_notice_title": {"en": "👋 Welcome to the Free Beta!", "es": "¡Bienvenido a la Beta Gratuita!"},
    "free_notice_text": {"en": "You are currently using the Free version. You will have to upgrade to Premium to analyze unlimited stocks, use Versus Mode, and keep your personalized Watchlist soon.", "es": "Actualmente estás usando la versión Gratuita. Próximamente deberás actualizar a Premium para analizar acciones ilimitadas, usar el Modo Versus y guardar tu Watchlist personalizada."},
    "pay_btn_soon": {"en": "💳 Upgrade to Premium - $2/month (Coming Soon)", "es": "💳 Mejorar a Premium - $2/mes (Próximamente)"},

    # Veredictos
    "very_safe": {"en": "Very Safe", "es": "Muy Segura"},
    "very_safe_t": {"en": "This company is a financial fortress. It has much more cash and short-term assets than debts, meaning it won't struggle to pay bills even if the economy stops. Its debt level is very low compared to its equity. It's a highly stable business that can withstand crises without bankruptcy risk.", "es": "Esta empresa es una fortaleza financiera. Tiene mucho más efectivo y activos a corto plazo que deudas, lo que significa que no tendrá problemas para pagar sus facturas incluso si la economía se detiene. Además, su nivel de deuda es muy bajo comparado con su propio capital. Es un negocio altamente estable que puede soportar crisis sin riesgo de quiebra."},
    "normal_risk": {"en": "Normal Risk", "es": "Riesgo Normal"},
    "normal_risk_t": {"en": "Financial health is okay. It can pay current obligations without sweating, but doesn't have a massive safety cushion. If there's a recession, it might feel pressure. Debt is at acceptable levels, but not solid enough to be completely shielded from prolonged economic storms.", "es": "La salud financiera está bien. Puede pagar sus obligaciones actuales sin despeinarse, pero no tiene un colchón de seguridad enorme. Si hay una recesión o un problema inesperado, podría sentir presión. La deuda está en niveles aceptables, pero no es tan sólida como para estar completamente blindada contra tormentas económicas prolongadas."},
    "risky": {"en": "Risky", "es": "Riesgosa"},
    "risky_t": {"en": "Caution: This company is walking on thin ice. It doesn't have enough cash to easily cover short-term debts. If sales drop or banks tighten conditions, it could face serious liquidity problems. Debt levels are high, magnifying risks and potentially leading to critical situations in tough times.", "es": "Precaución: Esta empresa está caminando sobre hielo delgado. No tiene suficiente efectivo para cubrir sus deudas a corto plazo con facilidad. Si las ventas caen o los bancos aprietan las condiciones, podría tener serios problemas de liquidez. El nivel de deuda es alto, lo que magnifica los riesgos y podría llevarla a situaciones críticas en tiempos difíciles."},
    "highly_profitable": {"en": "Highly Profitable", "es": "Muy Rentable"},
    "highly_profitable_t": {"en": "Excellent performance! This company is a money-making machine. It converts a huge portion of its sales into real profits and uses its assets extremely efficiently to generate shareholder value. It doesn't just sell a lot; it knows how to retain a mountain of cash after paying all operating expenses.", "es": "¡Excelente rendimiento! Esta empresa es una máquina de hacer dinero. Convierte una gran parte de sus ventas en ganancias reales y utiliza sus activos de manera extremadamente eficiente para generar valor a los accionistas. No solo vende mucho, sino que sabe retener una montaña de efectivo después de pagar todos sus gastos operativos."},
    "making_money": {"en": "Making Money", "es": "Gana Dinero"},
    "making_money_t": {"en": "The business is profitable and operates healthily. It's making money, which is the main thing, but there's still room for improvement. Profit margins might be moderate, or it might not be using all assets to full potential. It's a ship moving at a good pace, though not yet a top-tier racing sailboat.", "es": "El negocio es rentable y funciona de manera sana. Está ganando dinero, lo cual es lo principal, pero aún hay margen de mejora. Puede que sus márgenes de ganancia sean moderados o que no esté utilizando todos sus activos al máximo potencial. Es un barco que avanza a buen ritmo, aunque todavía no es un velero de máxima competición."},
    "struggling": {"en": "Struggling", "es": "Con Dificultades"},
    "struggling_t": {"en": "This company is having serious trouble being profitable. Its expenses are almost as high as its revenue, leaving very little (or zero) net profit. This could be because it's investing aggressively to grow, but if not, it simply has a business model with costs too high for what it generates.", "es": "Esta empresa está teniendo problemas serios para ser rentable. Sus gastos son casi tan altos como sus ingresos, dejando muy poco (o nada) de ganancia neta. Esto podría deberse a que está invirtiendo agresivamente para crecer, pero si no es así, simplemente tiene un modelo de negocio con costos demasiado elevados para lo que genera."},
    "great_value": {"en": "Great Value", "es": "Gran Oportunidad"},
    "great_value_t": {"en": "You're looking at a potential bargain! The stock price is very low compared to the profits it generates and the real value of its assets. The market seems to be underestimating this company. Buying at these prices gives you a great 'margin of safety', limiting downside risk while offering huge gains if the market corrects its mistake.", "es": "¡Estás mirando una ganga potencial! El precio de la acción es muy bajo en comparación con las ganancias que genera y el valor real de sus activos. El mercado parece estar subestimando a esta empresa. Comprar a estos precios te da un gran 'margen de seguridad', lo que limita tu riesgo si baja más, pero ofrece grandes ganancias si el mercado corrige su error."},
    "fair_price": {"en": "Fair Price", "es": "Precio Justo"},
    "fair_price_t": {"en": "The price is reasonable. You aren't buying at a fire sale, but you aren't being ripped off either. Financial multiples are at normal levels. You are paying what the company is reasonably worth today. To make money here, you'll rely on the company managing to consistently grow its sales and profits in the coming years.", "es": "El precio es razonable. No estás comprando a precio de remate, pero tampoco te están estafando. Los múltiplos financieros están en niveles normales. Estás pagando lo que la empresa vale razonablemente hoy. Para ganar dinero aquí, dependerás de que la empresa logre hacer crecer sus ventas y ganancias de forma constante en los próximos años."},
    "expensive": {"en": "Expensive", "es": "Precio Premium"},
    "expensive_t": {"en": "You are paying a very high premium for this stock. Investors are assuming this company will grow by leaps and bounds, driving its price up. If the company meets those sky-high expectations, great. But if growth slows even a little, the stock price could drop drastically.", "es": "Estás pagando una prima muy alta por esta acción. Los inversores están asumiendo que esta empresa va a crecer a pasos agigantados, por lo que han disparado su precio. Si la empresa cumple esas altísimas expectativas, genial. Pero si el crecimiento se desacelera aunque sea un poco, el precio de la acción podría caer de forma drástica."},
    "guide_current": {"en": "1.5 to 2.0 is ideal.", "es": "1.5 a 2.0 es ideal."},
    "guide_quick": {"en": "Should be ≥ 1.0.", "es": "Debe ser ≥ 1.0."},
    "guide_cash": {"en": "0.5 to 1 is safe.", "es": "0.5 a 1 es seguro."},
    "guide_debt": {"en": "Should be < 0.5.", "es": "Debe ser < 0.5."},
    "guide_inventory_t": {"en": "> 2 and < 9 is good.", "es": "> 2 y < 9 es bueno."},
    "guide_days_inv": {"en": "Lower is better.", "es": "Más bajo es mejor."},
    "guide_assets_t": {"en": "> 1.2x is strong.", "es": "> 1.2x es fuerte."},
    "guide_roe": {"en": "> 15% Excellent.", "es": "> 15% Excelente."},
    "guide_margin": {"en": "> 20% Highly Profitable.", "es": "> 20% Muy Rentable."},
    "guide_pe": {"en": "10-20 Ideal.", "es": "10-20 Ideal."},
    "guide_pcf": {"en": "10-15 Healthy.", "es": "10-15 Saludable."},
    "guide_ps": {"en": "< 2.0 Healthy.", "es": "< 2.0 Saludable."},
    "guide_pbv": {"en": "1-3 Standard.", "es": "1-3 Estándar."},
}

INVESTOR_QUOTES_EN = [
    ("Warren Buffett", "Price is what you pay. Value is what you get."),
    ("Peter Lynch", "Know what you own."),
    ("Charlie Munger", "Show me the incentive and I will show you the outcome.")
]
INVESTOR_QUOTES_ES = [
    ("Warren Buffett", "El precio es lo que pagas. El valor es lo que recibes."),
    ("Peter Lynch", "Conoce lo que posees."),
    ("Charlie Munger", "Muéstrame el incentivo y te mostraré el resultado.")
]

def get_random_quote(lang):
    if lang == "es": return random.choice(INVESTOR_QUOTES_ES)
    return random.choice(INVESTOR_QUOTES_EN)

def t(key):
    return T[key][st.session_state.lang]

# ============================================
# WATCHLIST
# ============================================
def load_watchlist():
    try:
        if os.path.exists(WATCHLIST_FILE):
            with open(WATCHLIST_FILE, "r") as f: return json.load(f)
    except: pass
    return []

def save_watchlist(wl):
    try:
        with open(WATCHLIST_FILE, "w") as f: json.dump(wl, f)
    except: pass

if "watchlist" not in st.session_state:
    st.session_state.watchlist = load_watchlist()

# ============================================
# BACKEND DATA
# ============================================
def get_company_description(symbol):
    try:
        info = yf.Ticker(symbol).info
        return info.get("longBusinessSummary") or info.get("businessSummary") or None
    except: return None

def get_data_av(sym):
    try:
        inc_resp = requests.get(AV_URL, params={"function": "INCOME_STATEMENT", "symbol": sym, "apikey": AV_KEY}).json()
        if "Note" in inc_resp: return "RATE_LIMIT"
        inc = inc_resp.get("annualReports", [])
        bs = requests.get(AV_URL, params={"function": "BALANCE_SHEET", "symbol": sym, "apikey": AV_KEY}).json().get("annualReports", [])
        cf = requests.get(AV_URL, params={"function": "CASH_FLOW", "symbol": sym, "apikey": AV_KEY}).json().get("annualReports", [])
        info_av = requests.get(AV_URL, params={"function": "OVERVIEW", "symbol": sym, "apikey": AV_KEY}).json()
        quote = requests.get(AV_URL, params={"function": "GLOBAL_QUOTE", "symbol": sym, "apikey": AV_KEY}).json().get("Global Quote", {})
        if len(inc) < 2 or len(bs) < 2: return None
        col1, col2 = "Year1", "Year2"
        d_inc = {"Total Revenue": [float(inc[0].get("totalRevenue", 0) or 0)], "Cost Of Revenue": [float(inc[0].get("costofGoodsAndServicesSold", 0) or 0)], "Net Income": [float(inc[0].get("netIncome", 0) or 0)]}
        d_bs = {"Total Current Assets": [float(bs[0].get("totalCurrentAssets", 0) or 0)], "Total Current Liabilities": [float(bs[0].get("totalCurrentLiabilities", 0) or 0)], "Inventory": [float(bs[0].get("inventory", 0) or 0)], "Cash And Cash Equivalents": [float(bs[0].get("cashAndCashEquivalentsAtCarryingValue", 0) or 0)], "Short Term Debt": [float(bs[0].get("shortTermDebt", 0) or 0)], "Long Term Debt": [float(bs[0].get("longTermDebt", 0) or 0)], "Stockholders Equity": [float(bs[0].get("totalShareholderEquity", 0) or 0)], "Total Assets": [float(bs[0].get("totalAssets", 0) or 0)]}
        d_cf = {"Operating Cash Flow": [float(cf[0].get("operatingCashflow", 0) or 0)]}
        df_inc = pd.DataFrame(d_inc, index=[col1]).T
        df_bs = pd.DataFrame(d_bs, index=[col1]).T
        df_cf = pd.DataFrame(d_cf, index=[col1]).T
        df_bs[col2] = [float(bs[1].get("totalCurrentAssets", 0) or 0), float(bs[1].get("totalCurrentLiabilities", 0) or 0), float(bs[1].get("inventory", 0) or 0), 0, 0, 0, float(bs[1].get("totalShareholderEquity", 0) or 0), float(bs[1].get("totalAssets", 0) or 0)]
        df_inc[col2] = ["", "", ""]
        info = {
            "shortName": info_av.get("Name", sym), "sector": info_av.get("Sector", "Unknown"), 
            "description": info_av.get("Description"),
            "currentPrice": float(quote.get("05. price", 0)) if quote.get("05. price") else None, 
            "sharesOutstanding": float(info_av.get("SharesOutstanding", 0)) if info_av.get("SharesOutstanding") else None, 
            "marketCap": float(info_av.get("MarketCapitalization", 0)) if info_av.get("MarketCapitalization") else None
        }
        return {"inc": df_inc, "bs": df_bs, "cf": df_cf, "info": info}
    except Exception as e: return str(e)

@st.cache_data(ttl=3600)
def get_data(symbol):
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        if "description" not in info: info["description"] = info.get("longBusinessSummary") or None
        
        # --- RESPALDO: Si Yahoo no trae el sector o descripción, usamos Alpha Vantage ---
        if not info.get("sector") or not info.get("description"):
            try:
                av_info = requests.get(AV_URL, params={"function": "OVERVIEW", "symbol": symbol, "apikey": AV_KEY}).json()
                if not info.get("sector"): info["sector"] = av_info.get("Sector", t("unknown_sector"))
                if not info.get("description"): info["description"] = av_info.get("Description")
            except: pass
        # --------------------------------------------------------------------------------------

        return {"inc": ticker.income_stmt, "bs": ticker.balance_sheet, "cf": ticker.cash_flow, "info": info}
    except: Exception as e:
        print(f"Error de Yahoo Finance para {symbol}: {e}") # Esto te mostrará el error real en la terminal
        av_data = get_data_av(symbol)
        if av_data == "RATE_LIMIT": st.warning(t("rate_limit")); st.stop()
        if isinstance(av_data, str): st.error(t("debug_err").format(err=av_data)); st.stop()
        if not av_data: st.error(t("no_data_av")); st.stop()
        return av_data

def sget(df, idx, col):
    try:
        if idx in df.index and col in df.columns:
            v = df.loc[idx, col]
            if isinstance(v, pd.Series): v = v.dropna().iloc[0]
            return float(v) if pd.notna(v) else None
    except: pass
    return None

def calc_all_13_ratios(sym):
    d = get_data(sym)
    if len(d["inc"].columns) < 2: return None, d["info"]
    info = d["info"]
    col, pcol = d["inc"].columns[0], d["inc"].columns[1]
    tca = sget(d["bs"], "Total Current Assets", col) or sget(d["bs"], "Current Assets", col)
    tcl = sget(d["bs"], "Total Current Liabilities", col) or sget(d["bs"], "Current Liabilities", col)
    inv = sget(d["bs"], "Inventory", col) or 0
    cash = sget(d["bs"], "Cash And Cash Equivalents", col) or sget(d["bs"], "Cash", col)
    td = (sget(d["bs"], "Short Term Debt", col) or 0) + (sget(d["bs"], "Long Term Debt", col) or 0)
    te = sget(d["bs"], "Stockholders Equity", col) or sget(d["bs"], "Stockholders' Equity", col)
    ta = sget(d["bs"], "Total Assets", col); pta = sget(d["bs"], "Total Assets", pcol)
    rev = sget(d["inc"], "Total Revenue", col)
    cogs = sget(d["inc"], "Cost Of Revenue", col) or sget(d["inc"], "Cost of Revenue", col)
    ni = sget(d["inc"], "Net Income", col)
    ocf = sget(d["cf"], "Operating Cash Flow", col)
    p_inv = sget(d["bs"], "Inventory", pcol) or 0
    avg_inv = (inv + p_inv) / 2; avg_ta = ((ta or 0) + (pta or 0)) / 2
    price = info.get("currentPrice") or info.get("regularMarketPrice")
    shares = info.get("sharesOutstanding")
    if not shares and price and info.get("marketCap"): shares = info["marketCap"] / price
    r = {}
    if tca and tcl and tcl != 0: r["Current Ratio"] = tca/tcl
    if tca and tcl and tcl != 0: r["Quick Ratio"] = (tca - inv)/tcl
    if cash and tcl and tcl != 0: r["Cash Ratio"] = cash/tcl
    if td and te and te != 0: r["Debt/Equity"] = td/te
    if cogs and avg_inv and avg_inv != 0: r["Inventory Turnover"] = cogs/avg_inv
    if "Inventory Turnover" in r and r["Inventory Turnover"] != 0: r["Days Inventory"] = 365/r["Inventory Turnover"]
    if rev and avg_ta and avg_ta != 0: r["Assets Turnover"] = rev/avg_ta
    if ni and te and te != 0: r["ROE"] = (ni/te)*100
    if ni and rev and rev != 0: r["Net Margin"] = (ni/rev)*100
    if price and ni and shares and (ni/shares) != 0: r["P/E Ratio"] = price/(ni/shares)
    if price and ocf and shares and (ocf/shares) != 0: r["P/CF Ratio"] = price/(ocf/shares)
    if price and rev and shares and (rev/shares) != 0: r["P/S Ratio"] = price/(rev/shares)
    if price and te and shares and (te/shares) != 0: r["P/BV Ratio"] = price/(te/shares)
    return r, info

def get_simple_verdicts(ratios):
    if not ratios: return {}
    v = {}
    safety_score = 0
    if ratios.get("Current Ratio", 0) >= 1.5: safety_score += 25
    elif ratios.get("Current Ratio", 0) >= 1: safety_score += 10
    if ratios.get("Quick Ratio", 0) >= 1: safety_score += 25
    elif ratios.get("Quick Ratio", 0) >= 0.5: safety_score += 10
    if ratios.get("Cash Ratio", 0) >= 0.5: safety_score += 25
    elif ratios.get("Cash Ratio", 0) >= 0.2: safety_score += 10
    if ratios.get("Debt/Equity", 100) <= 0.5: safety_score += 25
    elif ratios.get("Debt/Equity", 100) <= 1.5: safety_score += 10
    if safety_score >= 70: v["safety"] = ("🛡️", "very_safe")
    elif safety_score >= 40: v["safety"] = ("🟡", "normal_risk")
    else: v["safety"] = ("⚠️", "risky")
    profit_score = 0
    if ratios.get("ROE", 0) >= 15: profit_score += 35
    elif ratios.get("ROE", 0) >= 5: profit_score += 15
    if ratios.get("Net Margin", 0) >= 15: profit_score += 35
    elif ratios.get("Net Margin", 0) >= 5: profit_score += 15
    elif ratios.get("Net Margin", 0) >= 0: profit_score += 5
    if ratios.get("Assets Turnover", 0) >= 0.5: profit_score += 30
    elif ratios.get("Assets Turnover", 0) >= 0.25: profit_score += 15
    if profit_score >= 70: v["profit"] = ("💰", "highly_profitable")
    elif profit_score >= 40: v["profit"] = ("👍", "making_money")
    else: v["profit"] = ("📉", "struggling")
    value_score = 0
    pe, ps, pbv = ratios.get("P/E Ratio", 100), ratios.get("P/S Ratio", 100), ratios.get("P/BV Ratio", 100)
    pcf = ratios.get("P/CF Ratio", 100)
    if 0 < pe <= 15: value_score += 25
    elif 15 < pe <= 25: value_score += 15
    elif pe > 40: value_score -= 5
    if 0 < pcf <= 15: value_score += 25
    elif 15 < pcf <= 25: value_score += 15
    elif pcf > 40: value_score -= 5
    if ps <= 1.5: value_score += 25
    elif 1.5 < ps <= 3: value_score += 15
    elif ps > 7: value_score -= 5
    if pbv <= 1.5: value_score += 25
    elif 1.5 < pbv <= 3: value_score += 15
    elif pbv > 6: value_score -= 5
    if value_score >= 70: v["value"] = ("🎁", "great_value")
    elif value_score >= 30: v["value"] = ("💲", "fair_price")
    else: v["value"] = ("🚀", "expensive")
    v["total_score"] = max(0, min(100, int((safety_score + profit_score + value_score) / 3)))
    return v

def format_description(description, max_lines=5, max_chars_per_line=85):
    if not description: return None
    description = ' '.join(description.split())
    lines = textwrap.wrap(description, width=max_chars_per_line)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        if not lines[-1].endswith('...'): lines[-1] = lines[-1][:-3] + '...'
    return '\n'.join(lines)

# ============================================
# UI AUTH & NOTICE
# ============================================
def show_auth_screen():
    st.markdown(f"<h2 style='text-align: center; color: #0a3d6b;'>{t('auth_title')}</h2>", unsafe_allow_html=True)
    st.markdown(f"<p style='text-align: center; color: #666;'>{t('auth_subtitle')}</p>", unsafe_allow_html=True)
    tab_login, tab_register = st.tabs([t("login_tab"), t("register_tab")])
    
    with tab_login:
        with st.form("login_form"):
            email = st.text_input(t("email"), key="login_email")
            password = st.text_input(t("password"), type="password", key="login_pw")
            if st.form_submit_button(t("login_btn"), type="primary", width="stretch"):
                user = authenticate_user(email, password)
                if user:
                    st.session_state.logged_in = True
                    st.session_state.user_data = user
                    st.rerun()
                else: st.error(t("err_invalid_creds"))
                
    with tab_register:
        # Selector de género/avatar
        st.markdown(f"**{t('choose_avatar')}:**")
        
        col_hombre, col_mujer = st.columns(2)
        with col_hombre:
            btn_type_h = "primary" if st.session_state.selected_avatar == "👨" else "secondary"
            if st.button("👨 Hombre", key="reg_av_hombre", type=btn_type_h, width="stretch"):
                st.session_state.selected_avatar = "👨"
                st.rerun()
        with col_mujer:
            btn_type_m = "primary" if st.session_state.selected_avatar == "👩" else "secondary"
            if st.button("👩 Mujer", key="reg_av_mujer", type=btn_type_m, width="stretch"):
                st.session_state.selected_avatar = "👩"
                st.rerun()
        
        st.markdown("---")
        
        with st.form("register_form"):
            col_name, col_last = st.columns(2)
            with col_name:
                first_name = st.text_input(t("first_name"), key="reg_fname")
            with col_last:
                last_name = st.text_input(t("last_name"), key="reg_lname")
            email = st.text_input(t("email"), key="reg_email")
            password = st.text_input(t("password"), type="password", key="reg_pw")
            
            if st.form_submit_button(t("register_btn"), type="primary", width="stretch"):
                if register_user(email, password, first_name, last_name, st.session_state.selected_avatar):
                    st.success(t("reg_success"))
                else: 
                    st.error(t("err_user_exists"))

def show_free_notice():
    st.warning(f"**{t('free_notice_title')}** \n\n{t('free_notice_text')}")
    st.button(f"{t('pay_btn_soon')}", disabled=True, width="stretch")
    st.markdown("<br>", unsafe_allow_html=True)

# ============================================
# STOCK CARD DISPLAY
# ============================================
def display_stock_card(symbol):
    lang = st.session_state.lang
    ratios, info = calc_all_13_ratios(symbol)
    if not ratios: st.error(t("err_data").format(ticker=symbol)); return
    quote_author, quote_text = get_random_quote(lang)
    verdicts = get_simple_verdicts(ratios)
    score = verdicts["total_score"]
    name = info.get("shortName", symbol)
    sector = info.get("sector", t("unknown_sector"))
    description = info.get("description")
    price = info.get("currentPrice") or info.get("regularMarketPrice")
    formatted_description = format_description(description)
    col_name, col_price = st.columns([3, 1])
    with col_name:
        st.subheader(f"{name}")
        st.caption(f"{t('sector')}: {sector}")
        if formatted_description: st.caption(formatted_description)
    with col_price:
        if price: st.metric(label=t("current_price"), value=f"${price:.2f}")
        else: st.metric(label=t("current_price"), value=t("na"))
    if score >= 75: st.metric(label=t("health_score"), value=f"🟢 {score}/100")
    elif score >= 50: st.metric(label=t("health_score"), value=f"🔵 {score}/100")
    elif score >= 25: st.metric(label=t("health_score"), value=f"🟡 {score}/100")
    else: st.metric(label=t("health_score"), value=f"🔴 {score}/100")
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    with col1:
        s_emoji, s_key = verdicts["safety"]; s_title = t("safety"); s_verdict = t(s_key); s_text = t(f"{s_key}_t")
        if s_key == "very_safe": st.success(f"**{s_emoji} {s_title}**\n\n### {s_verdict}\n{s_text}")
        elif s_key == "normal_risk": st.warning(f"**{s_emoji} {s_title}**\n\n### {s_verdict}\n{s_text}")
        else: st.error(f"**{s_emoji} {s_title}**\n\n### {s_verdict}\n{s_text}")
    with col2:
        p_emoji, p_key = verdicts["profit"]; p_title = t("profitability"); p_verdict = t(p_key); p_text = t(f"{p_key}_t")
        if p_key == "highly_profitable": st.success(f"**{p_emoji} {p_title}**\n\n### {p_verdict}\n{p_text}")
        elif p_key == "making_money": st.warning(f"**{p_emoji} {p_title}**\n\n### {p_verdict}\n{p_text}")
        else: st.error(f"**{p_emoji} {p_title}**\n\n### {p_verdict}\n{p_text}")
    with col3:
        v_emoji, v_key = verdicts["value"]; v_title = t("price_value"); v_verdict = t(v_key); v_text = t(f"{v_key}_t")
        if v_key == "great_value": st.success(f"**{v_emoji} {v_title}**\n\n### {v_verdict}\n{v_text}")
        elif v_key == "fair_price": st.warning(f"**{v_emoji} {v_title}**\n\n### {v_verdict}\n{v_text}")
        else: st.error(f"**{v_emoji} {v_title}**\n\n### {v_verdict}\n{v_text}")
    st.markdown("---")
    st.info(f"💡 **{quote_author}**: *\"{quote_text}\"*")

# ============================================
# MAIN APP
# ============================================
def main():
    lang = st.session_state.lang
    
    col_logo, col_title = st.columns([3, 7])
    with col_logo: st.image("logo.png", width=450)
    with col_title:
        st.markdown("<h1 style='color: #0a3d6b; margin-top: 25px;'>Nivesha</h1>", unsafe_allow_html=True)
        st.markdown(f"<p style='color: #a0a0a0;'>{t('app_subtitle')}</p>", unsafe_allow_html=True)
    st.divider()
    
    if not st.session_state.logged_in:
        show_auth_screen()
    else:
        user_data = st.session_state.user_data
        
        # SIDEBAR
        with st.sidebar:
            # Panel de usuario con Avatar, Nombre y Apellido
            st.markdown(f"<h3 style='text-align: center;'>{user_data['avatar']} {user_data['first_name']} {user_data['last_name']}</h3>", unsafe_allow_html=True)
            st.caption(f"📧 {user_data['email']}")
            
            if st.button(t("logout"), width="stretch"):
                st.session_state.logged_in = False
                st.session_state.user_data = None
                st.rerun()
            st.markdown("---")
            
            col_en, col_es = st.columns(2)
            with col_en:
                btn_type_en = "primary" if lang == "en" else "secondary"
                if st.button("🇺🇸 English", key="lang_en", width="stretch", type=btn_type_en):
                    st.session_state.lang = "en"; st.rerun()
            with col_es:
                btn_type_es = "primary" if lang == "es" else "secondary"
                if st.button("🇪🇸 Español", key="lang_es", width="stretch", type=btn_type_es):
                    st.session_state.lang = "es"; st.rerun()
            st.markdown("---")
            st.header(t("watchlist_header"))
            with st.form("add_watchlist_form", clear_on_submit=True):
                new_ticker = st.text_input(t("add_ticker"), placeholder=t("placeholder_ticker"))
                submitted = st.form_submit_button(t("add_button"))
                if submitted and new_ticker:
                    clean_ticker = new_ticker.strip().upper()
                    if clean_ticker not in st.session_state.watchlist:
                        st.session_state.watchlist.append(clean_ticker)
                        save_watchlist(st.session_state.watchlist)
                        st.success(t("added_msg").format(ticker=clean_ticker))
                    else: st.warning(t("already_in_list").format(ticker=clean_ticker))
            st.markdown("---")
            if not st.session_state.watchlist: st.info(t("empty_list"))
            else:
                for tick in st.session_state.watchlist:
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        if st.button(f"🔍 {tick}", key=f"wl_{tick}", width="stretch"): st.session_state.active_ticker = tick
                    with col2:
                        if st.button("❌", key=f"del_{tick}"):
                            st.session_state.watchlist.remove(tick)
                            save_watchlist(st.session_state.watchlist)
                            st.rerun()
                if st.button(t("clear_list")):
                    st.session_state.watchlist = []
                    save_watchlist(st.session_state.watchlist)
                    st.rerun()

        show_free_notice()

        tab_single, tab_vs = st.tabs([t("tab_single"), t("tab_vs")])
        if "active_ticker" not in st.session_state: st.session_state.active_ticker = "AAPL"

        with tab_single:
            symbol_input = st.text_input(t("enter_ticker"), value=st.session_state.active_ticker, key="single_input")
            if st.button(t("check_stock"), type="primary", key="single_btn"):
                display_stock_card(symbol_input.strip().upper())
                with st.expander(t("price_history")):
                    try:
                        hist = yf.Ticker(symbol_input.strip().upper()).history(period="2y")
                        st.line_chart(hist["Close"], height=300)
                    except: st.warning(t("load_history_err"))
                with st.expander(t("geek_mode")):
                    ratios, _ = calc_all_13_ratios(symbol_input.strip().upper())
                    if ratios:
                        guides = {"Current Ratio": t("guide_current"), "Quick Ratio": t("guide_quick"), "Cash Ratio": t("guide_cash"), "Debt/Equity": t("guide_debt"), "Inventory Turnover": t("guide_inventory_t"), "Days Inventory": t("guide_days_inv"), "Assets Turnover": t("guide_assets_t"), "ROE": t("guide_roe"), "Net Margin": t("guide_margin"), "P/E Ratio": t("guide_pe"), "P/CF Ratio": t("guide_pcf"), "P/S Ratio": t("guide_ps"), "P/BV Ratio": t("guide_pbv")}
                        ratio_df = pd.DataFrame.from_dict(ratios, orient='index', columns=[t("value")])
                        ratio_df.index.name = t("ratio")
                        ratio_df[t("unit")] = ratio_df.index.map(lambda x: "%" if x in ["ROE", "Net Margin"] else "x")
                        ratio_df[t("what_to_see")] = ratio_df.index.map(guides)
                        st.dataframe(ratio_df, width="stretch")

        with tab_vs:
            st.markdown(f"### {t('vs_intro')}")
            col_a, col_b = st.columns(2)
            with col_a: fighter_a = st.text_input(t("stock_a"), value="AAPL", key="vs_a")
            with col_b: fighter_b = st.text_input(t("stock_b"), value="MSFT", key="vs_b")
            if st.button(t("fight_btn"), type="primary", key="vs_btn"):
                c1, c2 = st.columns(2)
                score_a, score_b = None, None
                with c1:
                    try:
                        ratios_a, _ = calc_all_13_ratios(fighter_a.strip().upper())
                        if ratios_a: score_a = get_simple_verdicts(ratios_a)["total_score"]
                    except: pass
                with c2:
                    try:
                        ratios_b, _ = calc_all_13_ratios(fighter_b.strip().upper())
                        if ratios_b: score_b = get_simple_verdicts(ratios_b)["total_score"]
                    except: pass
                if score_a is not None and score_b is not None:
                    if score_a > score_b: winner_text = t("wins_by").format(winner=fighter_a.strip().upper(), diff=score_a - score_b)
                    elif score_b > score_a: winner_text = t("wins_by").format(winner=fighter_b.strip().upper(), diff=score_b - score_a)
                    else: winner_text = t("tie")
                    st.success(winner_text); st.divider()
                    col_left, col_right = st.columns(2)
                    with col_left: display_stock_card(fighter_a.strip().upper())
                    with col_right: display_stock_card(fighter_b.strip().upper())
                else: st.error(t("err_one_or_both"))

if __name__ == "__main__":
    main()
