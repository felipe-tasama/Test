from pathlib import Path
import json
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'data'; DOCS=ROOT/'docs'

def payoff(stock,strike,kind):
    x=np.asarray(stock,dtype=float)
    return np.maximum(x-strike,0) if kind=='call' else np.maximum(strike-x,0)

def crr(spot,strike,T,r,sigma,N,q=0,kind='call',american=False,tree_steps=3):
    if min(spot,strike,T,sigma,N)<=0: raise ValueError('Spot, strike, maturity, volatility, and steps must be positive.')
    if kind not in {'call','put'}: raise ValueError('kind must be call or put.')
    N=int(N); dt=T/N; u=np.exp(sigma*np.sqrt(dt)); d=1/u; growth=np.exp((r-q)*dt); p=(growth-d)/(u-d); disc=np.exp(-r*dt)
    if not(d<growth<u and 0<p<1): raise ValueError('No-arbitrage condition failed: risk-neutral probability is outside (0,1).')
    j=np.arange(N+1); stocks=spot*u**j*d**(N-j); values=payoff(stocks,strike,kind); exercised=[]
    for n in range(N-1,-1,-1):
        values=disc*(p*values[1:n+2]+(1-p)*values[:n+1])
        if american:
            j=np.arange(n+1); stocks=spot*u**j*d**(n-j); intrinsic=payoff(stocks,strike,kind); mask=intrinsic>values+1e-12
            if mask.any(): exercised.append({'step':n,'min_stock':float(stocks[mask].min()),'max_stock':float(stocks[mask].max())})
            values=np.maximum(values,intrinsic)
    n=min(tree_steps,N); dts=T/n; us=np.exp(sigma*np.sqrt(dts)); ds=1/us; ps=(np.exp((r-q)*dts)-ds)/(us-ds); discs=np.exp(-r*dts)
    st=[[float(spot*us**j*ds**(i-j)) for j in range(i+1)] for i in range(n+1)]
    opt=[float(x) for x in payoff(st[-1],strike,kind)]; ot=[None]*(n+1); ot[n]=opt[:]
    for i in range(n-1,-1,-1):
        opt=[float(discs*(ps*opt[j+1]+(1-ps)*opt[j])) for j in range(i+1)]
        if american: opt=[max(x,float(payoff(st[i][j],strike,kind))) for j,x in enumerate(opt)]
        ot[i]=opt[:]
    return {'price':float(values[0]),'u':float(u),'d':float(d),'p_star':float(p),'dt':float(dt),'stock_tree':st,'option_tree':ot,'early_exercise':list(reversed(exercised))}

def price_only(m, **changes):
    x={**m,**changes}; return crr(x['spot'],x['strike'],x['maturity_years'],x['risk_free_rate'],x['volatility'],x['lattice_steps'],x['dividend_yield'],x['option_type'],x['exercise_style']=='american')['price']

def greek_analysis(m):
    """Measure local risk in dollars per option share unless otherwise stated."""
    S, T = m['spot'], m['maturity_years']
    K, r, q, sigma = (m[k] for k in ('strike', 'risk_free_rate', 'dividend_yield', 'volatility'))
    n = m['lattice_steps']
    american = m['exercise_style'] == 'american'

    def price(**changes):
        return price_only(m, **changes)

    def derivatives(spot):
        # Recover the first two levels of the original lattice with subtrees.
        dt = T / n
        u = np.exp(sigma * np.sqrt(dt))
        d = 1 / u

        def node(level, ups):
            stock = spot * u**ups * d**(level-ups)
            return stock, price(spot=stock, maturity_years=T-level*dt, lattice_steps=n-level)

        sl, vl = node(1, 0)
        sh, vh = node(1, 1)
        s0, v0 = node(2, 0)
        s1, v1 = node(2, 1)
        s2, v2 = node(2, 2)
        return (vh-vl)/(sh-sl), 2*((v2-v1)/(s2-s1)-(v1-v0)/(s1-s0))/(s2-s0), (v1-price(spot=spot))/(2*dt*365)

    def slope(key, center, h, **changes):
        return (price(**(changes | {key: center+h}))-price(**(changes | {key: center-h})))/(2*h)

    def richardson(key, center, h, **changes):
        return (4*slope(key, center, h/2, **changes)-slope(key, center, h, **changes))/3

    delta, gamma, theta = derivatives(S)
    vega = richardson('volatility', sigma, .005)*.01
    rho = richardson('risk_free_rate', r, .001)*.01
    greeks = dict(delta=delta, gamma=gamma, vega_1pct=vega, theta_1day=theta, rho_1pct=rho)
    base = price()

    def fd(h):
        up, dn = price(spot=S+h), price(spot=S-h)
        return (up-dn)/(2*h), (up-2*base+dn)/h**2

    h = S*.02
    delta_fd, gamma_fd = fd(h)
    delta_alt, gamma_alt = fd(h*1.5)
    day = 1/365
    checks = [
        ('Delta', delta, delta_fd, delta_alt, h, h*1.5, 'option $ per stock $'),
        ('Gamma', gamma, gamma_fd, gamma_alt, h, h*1.5, 'delta change per stock $'),
        ('Vega', vega, slope('volatility',sigma,.01)*.01, slope('volatility',sigma,.005)*.01, .01, .005, 'option $ per +1 volatility point'),
        ('Theta', theta, price(maturity_years=T-day)-base, (price(maturity_years=T-2*day)-base)/2, day, 2*day, 'option $ per calendar day elapsed'),
        ('Rho', rho, slope('risk_free_rate',r,.002)*.01, slope('risk_free_rate',r,.001)*.01, .002, .001, 'option $ per +1 rate point'),
    ]
    rows = [dict(greek=name, primary=a, finite_difference=b, alternative=c, bump=x,
                 alternative_bump=y, difference=a-b, units=units)
            for name,a,b,c,x,y,units in checks]
    ds, dv, dr, elapsed = 1, .01, .001, 1
    stock_reprice = price(spot=S+ds)-base
    combined_reprice = price(spot=S+ds, volatility=sigma+dv, risk_free_rate=r+dr,
                             maturity_years=T-elapsed/365)-base
    linear = delta*ds
    curved = linear + .5*gamma*ds**2
    combined = curved + vega*dv/.01 + theta*elapsed + rho*dr/.01
    repricing = [dict(method=name, estimate=estimate, full_reprice=actual, error=estimate-actual)
                 for name,estimate,actual in [('Delta only',linear,stock_reprice),
                 ('Delta and gamma',curved,stock_reprice),('Combined',combined,combined_reprice)]]
    single_factor = [
        dict(shock='Volatility +1 point',estimate=vega,actual=price(volatility=sigma+dv)-base),
        dict(shock='One calendar day elapsed',estimate=theta,actual=price(maturity_years=T-day)-base),
        dict(shock='Rate +10 basis points',estimate=rho*.1,actual=price(risk_free_rate=r+dr)-base),
    ]
    curve = []
    for stock in np.linspace(.75*min(S,K), 1.25*max(S,K), 61):
        de, ga, th = derivatives(float(stock))
        ve = richardson('volatility', sigma, .005, spot=float(stock))*.01
        curve.append(dict(spot=stock, delta=de, gamma=ga, vega_1pct=ve, theta_1day=th))
    euro = price(exercise_style='european')
    lo = max(S-K, 0) if m['option_type']=='call' else max(K-S, 0)
    hi = S if m['option_type']=='call' else K
    return dict(greeks=greeks, greek_validation=rows, repricing=repricing,
                single_factor=single_factor, greek_curve=curve, european_price=euro,
                exercise_premium=base-euro, american_bounds_pass=not american or lo <= base <= hi,
                delta_check=bool(0 <= delta <= 1 if m['option_type']=='call' else -1 <= delta <= 0),
                gamma_check=bool(gamma >= -1e-10))


def build_results(data=DATA):
    inp=pd.read_csv(data/'company_inputs.csv'); targets=pd.read_csv(data/'analyst_targets.csv'); sources=pd.read_csv(data/'source_documentation.csv')
    if len(inp)!=1: raise ValueError('company_inputs.csv must contain exactly one row.')
    m=inp.iloc[0].to_dict(); nums=['spot','strike','maturity_years','risk_free_rate','dividend_yield','volatility','market_bid','market_ask','dcf_value','comps_value']
    for k in nums: m[k]=float(m[k])
    m['lattice_steps']=int(m['lattice_steps']); m['option_type']=str(m['option_type']).lower(); m['exercise_style']=str(m['exercise_style']).lower(); m['market_mid']=(m['market_bid']+m['market_ask'])/2
    if m['market_bid']>m['market_ask']: raise ValueError('market_bid cannot exceed market_ask.')
    if m['option_type'] not in {'call','put'} or m['exercise_style'] not in {'european','american'}: raise ValueError('Unsupported option type or exercise style.')
    if len(targets)<5 or not targets.target.gt(0).all() or targets.horizon_months.nunique()!=1: raise ValueError('Use five or more positive targets with one common horizon.')
    required={'spot','option_contract','market_bid_ask','volatility','risk_free_rate','dividend_yield','dcf_value','comps_value','analyst_targets'}
    missing=required-set(sources.input.astype(str));
    if missing: raise ValueError('Missing source documentation: '+', '.join(sorted(missing)))
    stats={'count':int(len(targets)),'mean':float(targets.target.mean()),'median':float(targets.target.median()),'std':float(targets.target.std(ddof=1)),'min':float(targets.target.min()),'max':float(targets.target.max()),'q1':float(targets.target.quantile(.25)),'q3':float(targets.target.quantile(.75))}
    qm={'Severe bear':.05,'Bear':.25,'Base':.50,'Bull':.75,'Tail':.95}; w={'Severe bear':.10,'Bear':.20,'Base':.40,'Bull':.20,'Tail':.10}
    states=pd.DataFrame({'state':list(qm),'quantile':list(qm.values()),'terminal_price':[float(targets.target.quantile(q)) for q in qm.values()],'subjective_weight':[w[k] for k in qm]})
    states['option_payoff']=payoff(states.terminal_price,m['strike'],m['option_type']); states['weighted_payoff']=states.subjective_weight*states.option_payoff
    df=float(np.exp(-m['risk_free_rate']*m['maturity_years'])); states['discounted_contribution']=df*states.weighted_payoff; belief=float(states.discounted_contribution.sum())
    lattice=crr(m['spot'],m['strike'],m['maturity_years'],m['risk_free_rate'],m['volatility'],m['lattice_steps'],m['dividend_yield'],m['option_type'],m['exercise_style']=='american')
    steps=[25,50,100,200,500]; conv=[price_only(m,lattice_steps=n) for n in steps]
    pvs=m['spot']*np.exp(-m['dividend_yield']*m['maturity_years']); pvk=m['strike']*np.exp(-m['risk_free_rate']*m['maturity_years']); lo,hi=(max(pvs-pvk,0),pvs) if m['option_type']=='call' else (max(pvk-pvs,0),pvk)
    call=crr(m['spot'],m['strike'],m['maturity_years'],m['risk_free_rate'],m['volatility'],m['lattice_steps'],m['dividend_yield'],'call')['price']; put=crr(m['spot'],m['strike'],m['maturity_years'],m['risk_free_rate'],m['volatility'],m['lattice_steps'],m['dividend_yield'],'put')['price']; parity=float((call-put)-(pvs-pvk))
    base=lattice['price']
    sigmas=np.linspace(max(.05,m['volatility']-.15),m['volatility']+.15,25); sensitivity=[{'volatility':float(x),'price':price_only(m,volatility=float(x))} for x in sigmas]
    spread=m['market_ask']-m['market_bid']; status='Inside spread' if m['market_bid']<=base<=m['market_ask'] else ('Below bid' if base<m['market_bid'] else 'Above ask')
    return {'model':m,'analyst_targets':[float(x) for x in targets.target],'analyst_stats':stats,'valuation':{'Current market':m['spot'],'Comparable companies':m['comps_value'],'Student DCF':m['dcf_value'],'Analyst median':stats['median']},'states':states.to_dict('records'),'valuation_weighted_expected_payoff':belief,'belief_decomposition':{'weight_zero_payoff':float(states.loc[states.option_payoff==0,'subjective_weight'].sum()),'weight_positive_payoff':float(states.loc[states.option_payoff>0,'subjective_weight'].sum()),'weighted_terminal_payoff':float(states.weighted_payoff.sum()),'discount_factor':df},'lattice':lattice,**greek_analysis(m),'validation':{'valid_risk_neutral_probability':bool(0<lattice['p_star']<1),'inside_theoretical_bounds':bool(lo<=base<=hi),'put_call_parity_pass':bool(abs(parity)<.05) if m['exercise_style']=='european' else None,'parity_residual':parity,'convergence_pass':bool(abs(conv[-1]-conv[-2])<.05),'convergence_gap':conv[-1]-conv[-2],'lower_bound':lo,'upper_bound':hi},'convergence':[{'steps':n,'price':float(x)} for n,x in zip(steps,conv)],'comparison':{'Analyst scenario':belief,'CRR lattice':base,'Market midpoint':m['market_mid']},'market_comparison':{'model_minus_mid':base-m['market_mid'],'model_minus_mid_pct':(base/m['market_mid']-1) if m['market_mid'] else None,'spread':spread,'spread_pct':spread/m['market_mid'] if m['market_mid'] else None,'status':status},'sensitivity':sensitivity,'analyst_horizon_years':float(targets.horizon_months.iloc[0])/12,'sources':sources.to_dict('records')}

if __name__=='__main__':
    DOCS.mkdir(exist_ok=True); out=build_results(); (DOCS/'model_results.json').write_text(json.dumps(out,indent=2)); print('Exported docs/model_results.json')
