const $=s=>document.querySelector(s), money=x=>'$'+Number(x).toLocaleString(undefined,{minimumFractionDigits:2,maximumFractionDigits:2});let BASE,weights={};
function payoff(s,k,t){return t==='call'?Math.max(s-k,0):Math.max(k-s,0)}
function crr(S,K,T,r,sig,N,q,type,american){N=Math.round(N);if(!(S>0&&K>0&&T>0&&sig>0&&N>0))throw Error('Spot, strike, maturity, volatility, and steps must be positive.');let dt=T/N,u=Math.exp(sig*Math.sqrt(dt)),dn=1/u,p=(Math.exp((r-q)*dt)-dn)/(u-dn),disc=Math.exp(-r*dt);if(!(p>0&&p<1))throw Error('No-arbitrage probability is outside (0,1).');let a=Array.from({length:N+1},(_,j)=>payoff(S*u**j*dn**(N-j),K,type));for(let n=N-1;n>=0;n--){a=Array.from({length:n+1},(_,j)=>disc*(p*a[j+1]+(1-p)*a[j]));if(american)a=a.map((v,j)=>Math.max(v,payoff(S*u**j*dn**(n-j),K,type)))}return {price:a[0],p}}
fetch('model_results.json',{cache:'no-store'}).then(r=>{if(!r.ok)throw Error('Model results are missing.');return r.json()}).then(d=>{BASE=d;weights=Object.fromEntries(d.states.map(z=>[z.state,z.subjective_weight]));render(d)}).catch(e=>$('#app').innerHTML=`<section class="card warn"><h2>Dashboard unavailable</h2><p>${e.message}</p></section>`);
function recalc(){try{let d=structuredClone(BASE),m=d.model;d.sandbox=true;['spot','strike','maturity_years','risk_free_rate','dividend_yield','volatility','lattice_steps','market_bid','market_ask'].forEach(x=>m[x]=Number($('#'+x).value));m.option_type=$('#option_type').value;m.exercise_style=$('#exercise_style').value;if(m.market_bid>m.market_ask)throw Error('Bid cannot exceed ask.');let z=crr(m.spot,m.strike,m.maturity_years,m.risk_free_rate,m.volatility,m.lattice_steps,m.dividend_yield,m.option_type,m.exercise_style==='american');d.lattice.price=z.price;d.lattice.p_star=z.p;m.market_mid=(m.market_bid+m.market_ask)/2;let total=Object.values(weights).reduce((a,b)=>a+b,0);if(Object.values(weights).some(w=>w<0||w>1))throw Error('Each scenario weight must be between 0% and 100%.');if(Math.abs(total-1)>.0001)throw Error('Scenario weights must total 100%.');d.states.forEach(s=>{s.subjective_weight=weights[s.state];s.option_payoff=payoff(s.terminal_price,m.strike,m.option_type);s.discounted_contribution=Math.exp(-m.risk_free_rate*m.maturity_years)*s.subjective_weight*s.option_payoff});d.valuation_weighted_expected_payoff=d.states.reduce((a,s)=>a+s.discounted_contribution,0);d.comparison={'Analyst scenario':d.valuation_weighted_expected_payoff,'CRR lattice':z.price,'Market midpoint':m.market_mid};render(d)}catch(e){$('#message').textContent=e.message;$('#message').className='notice warn'}}
function render(d){let m=d.model,s=d.states,mc=d.market_comparison||{};$('#app').innerHTML=`<div id="message" class="notice">${d.sandbox?'Sandbox recalculated. The Greek analysis below uses the documented KO baseline.':'Documented KO baseline loaded.'}</div><section class="grid">
${[['Spot',m.spot],['CRR value',d.lattice.price],['Market midpoint',m.market_mid],['Belief payoff',d.valuation_weighted_expected_payoff]].map(x=>`<article class="card kpi"><span class="sub">${x[0]}</span><b>${money(x[1])}</b></article>`).join('')}
<article class="card span12"><h2>Interactive pricing sandbox</h2><div class="controls">${[['spot','Spot'],['strike','Strike'],['maturity_years','Years'],['risk_free_rate','Risk-free rate (decimal)'],['dividend_yield','Dividend yield (decimal)'],['volatility','Volatility (decimal)'],['lattice_steps','Lattice steps'],['market_bid','Market bid'],['market_ask','Market ask']].map(x=>`<label>${x[1]}<input id="${x[0]}" type="number" step="any" value="${m[x[0]]}"></label>`).join('')}<label>Option type<select id="option_type"><option ${m.option_type==='call'?'selected':''}>call</option><option ${m.option_type==='put'?'selected':''}>put</option></select></label><label>Exercise<select id="exercise_style"><option ${m.exercise_style==='european'?'selected':''}>european</option><option ${m.exercise_style==='american'?'selected':''}>american</option></select></label><button id="calc" class="btn" type="button">Recalculate</button><button id="reset" class="btn alt" type="button">Reset</button></div></article>
<article class="card span8"><h2>Price comparison</h2><div id="compare" class="plot"></div></article><article class="card span4"><h2>Market interpretation</h2><p class="status">${m.market_bid<=d.lattice.price&&d.lattice.price<=m.market_ask?'Inside quoted spread':d.lattice.price<m.market_bid?'Below bid':'Above ask'}</p><p>Model minus midpoint: <b>${money(d.lattice.price-m.market_mid)}</b></p><p>Bid-ask spread: <b>${money(m.market_ask-m.market_bid)}</b></p><p>Risk-neutral probability: <b>${(100*d.lattice.p_star).toFixed(2)}%</b></p></article>
<article class="card span6"><h2>Volatility sensitivity</h2><div id="sens" class="plot"></div></article><article class="card span6"><h2>Lattice convergence</h2><div id="conv" class="plot"></div></article>
<article class="card span12"><h2>Editable scenario weights</h2><p class="sub">These are subjective belief weights, not CRR probabilities. Total must equal 100%.</p><div class="weights">${s.map(z=>`<label>${z.state}<input data-weight="${z.state}" type="number" min="0" max="100" step="1" value="${(100*z.subjective_weight).toFixed(0)}">%</label>`).join('')}</div><p id="weightTotal"></p></article>
<article class="card span6"><h2>Scenario payoff</h2><div id="payoff" class="plot"></div></article><article class="card span6"><h2>KO baseline Greeks</h2><table><tbody>${(d.greek_validation||[]).map(g=>`<tr><td>${g.greek}</td><td>${g.primary.toFixed(4)} ${g.units}</td></tr>`).join('')}</tbody></table></article>
<article class="card span12"><h2>KO baseline model checks</h2><p>Bounds: ${d.validation.inside_theoretical_bounds?'Pass':'Fail'} · Convergence: ${d.validation.convergence_pass?'Pass':'Fail'} · Risk-neutral probability: ${d.validation.valid_risk_neutral_probability?'Pass':'Fail'} · Put-call parity: ${d.validation.put_call_parity_pass===null?'Not applicable to American selection':d.validation.put_call_parity_pass?'Pass':'Fail'}</p></article>${greekCharts.map(([key,title])=>`<article class="card span6"><h2>${title}</h2><div id="greek-${key}" class="plot"></div></article>`).join('')}<p class="foot span12">KO baseline uses the November 19, 2026 quote. Sources and methods are documented in the repository.</p></section>`;
$('#calc').addEventListener('click',recalc);$('#reset').addEventListener('click',()=>{weights=Object.fromEntries(BASE.states.map(z=>[z.state,z.subjective_weight]));render(structuredClone(BASE))});document.querySelectorAll('[data-weight]').forEach(e=>e.addEventListener('input',()=>{weights[e.dataset.weight]=Number(e.value)/100;showTotal()}));showTotal();draw(d);drawGreekCharts(BASE)}
function showTotal(){let n=Object.values(weights).reduce((a,b)=>a+b,0);$('#weightTotal').textContent='Total: '+(100*n).toFixed(0)+'%';$('#weightTotal').className=Math.abs(n-1)<.0001?'notice':'notice warn'}
function draw(d){let cfg={responsive:true,displaylogo:false};let c=Object.entries(d.comparison),m=d.model,s=d.states;Plotly.newPlot('compare',[{type:'bar',x:c.map(x=>x[0]),y:c.map(x=>x[1]),text:c.map(x=>money(x[1])),textposition:'outside',marker:{color:['#0f9188','#197ba6','#c78a12']}}],{margin:{l:55,r:20,t:25,b:70},yaxis:{tickprefix:'$'},shapes:[{type:'rect',xref:'paper',x0:0,x1:1,y0:m.market_bid,y1:m.market_ask,fillcolor:'rgba(199,138,18,.12)',line:{width:0}}]},cfg);let sens=Array.from({length:25},(_,i)=>Math.max(.05,m.volatility-.15)+i*.3/24).map(x=>({x,y:crr(m.spot,m.strike,m.maturity_years,m.risk_free_rate,x,m.lattice_steps,m.dividend_yield,m.option_type,m.exercise_style==='american').price}));Plotly.newPlot('sens',[{type:'scatter',mode:'lines',x:sens.map(z=>z.x),y:sens.map(z=>z.y),line:{color:'#197ba6',width:4}}],{margin:{l:55,r:20,t:25,b:55},xaxis:{tickformat:'.0%',title:'Volatility'},yaxis:{tickprefix:'$',title:'Option value'}},cfg);Plotly.newPlot('conv',[{type:'scatter',mode:'lines+markers',x:d.convergence.map(z=>z.steps),y:d.convergence.map(z=>z.price),line:{color:'#0f9188'}}],{margin:{l:55,r:20,t:25,b:55},xaxis:{title:'Steps'},yaxis:{tickprefix:'$',title:'Option value'}},cfg);Plotly.newPlot('payoff',[{type:'bar',x:s.map(z=>z.state),y:s.map(z=>z.option_payoff),marker:{color:'#e26522'},text:s.map(z=>money(z.option_payoff)),textposition:'outside'}],{margin:{l:55,r:20,t:25,b:70},yaxis:{tickprefix:'$',title:'Payoff'}},cfg)}

const greekCharts = [
  ['delta', 'Delta vs. KO stock price', 'Option $ per stock $'],
  ['gamma', 'Gamma vs. KO stock price', 'Delta change per stock $'],
  ['vega_1pct', 'Vega vs. KO stock price', 'Option $ per +1 volatility point'],
  ['theta_1day', 'Theta vs. KO stock price', 'Option $ per day elapsed'],
];

function drawGreekCharts(data) {
  const curve = data.greek_curve;
  if (!curve) return;
  for (const [key, title, units] of greekCharts) {
    const lines = [
      [data.model.spot, 'Current spot', '#197ba6'],
      [data.model.strike, 'Strike', '#c78a12'],
    ].map(([x, name, color]) => ({
      type: 'scatter', mode: 'lines', x: [x, x],
      y: [Math.min(...curve.map(row => row[key])), Math.max(...curve.map(row => row[key]))],
      name, line: { color, dash: 'dot' },
      hovertemplate: name + ' $%{x:.2f}<extra></extra>',
    }));
    Plotly.newPlot('greek-' + key, [{
      type: 'scatter', mode: 'lines', name: title,
      x: curve.map(row => row.spot), y: curve.map(row => row[key]),
      hovertemplate: 'KO $%{x:.2f}<br>%{y:.4f} ' + units + '<extra></extra>',
      line: { color: '#0f9188', width: 3 },
    }, ...lines], {
      margin: { l: 76, r: 20, t: 12, b: 78 },
      xaxis: { title: 'KO stock price ($)' },
      yaxis: { title: units, automargin: true },
      legend: { orientation: 'h', y: -.24 },
    }, { responsive: true, displaylogo: false });
  }
}
