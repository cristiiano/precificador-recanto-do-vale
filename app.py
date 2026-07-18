# app.py - Precificador de Imóveis - Recanto do Vale / Vargas
# Imobiliárias: Besser, Corretor e Cia, Sauthier, Imobiliária Sapucaia, Andi Imóveis

from flask import Flask, request, jsonify
import requests
from bs4 import BeautifulSoup
import re
import os

app = Flask(__name__)

class PrecificadorRecantoDoVale:
    def __init__(self):
        self.imoveis_encontrados = []
        
        # IMOBILIÁRIAS CADASTRADAS
        self.imobiliarias = {
            'besser': {
                'nome': 'Besser Negócios Imobiliários',
                'url': 'https://www.imobiliariabesser.com.br/imoveis/sapucaia-do-sul/recanto-do-vale',
                'url_base': 'https://www.imobiliariabesser.com.br',
                'telefone': '(51) 3459-2222',
                'cor': '#2196F3'
            },
            'corretorcia': {
                'nome': 'Corretor e Cia',
                'url': 'https://www.corretorecia.com/imobiliaria/venda/casa/recanto-do-vale/sapucaia-do-sul-rs/imoveis/',
                'url_base': 'https://www.corretorecia.com',
                'telefone': '(51) 3474-1212',
                'cor': '#9C27B0'
            },
            'sauthier': {
                'nome': 'Sauthier Imóveis',
                'url': 'https://www.sauthier.com.br/Imovel/Venda/Casa/Vargas/Sapucaia-Do-Sul/RS/',
                'url_base': 'https://www.sauthier.com.br',
                'telefone': '(51) 3474-1111',
                'cor': '#FF5722'
            },
            'sapucaia': {
                'nome': 'Imobiliária Sapucaia',
                'url': 'https://www.imobiliariasapucaia.com.br/imoveis/a-venda/sapucaia-do-sul/vargas-sapucaia-do-sul',
                'url_base': 'https://www.imobiliariasapucaia.com.br',
                'telefone': '(51) 3474-0000',
                'cor': '#00BCD4'
            },
            'andi': {
                'nome': 'Andi Imóveis',
                'url': 'https://andiimoveis.com.br/comprar/rs/sapucaia-do-sul/vargas/casa/ordem-valor/resultado/pagina-1/',
                'url_base': 'https://andiimoveis.com.br',
                'telefone': 'Ver no site',
                'cor': '#E91E63',
                'paginacao': True,
                'url_pagina': 'https://andiimoveis.com.br/comprar/rs/sapucaia-do-sul/vargas/casa/ordem-valor/resultado/pagina-{pagina}/',
                'max_paginas': 5
            }
        }
    
    def buscar_site(self, config, tipo=None, preco_min=0, preco_max=999999999, area_min=0, area_max=999999):
        """Busca imóveis em um site específico"""
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'pt-BR,pt;q=0.9',
        }
        
        todos_imoveis = []
        urls_para_buscar = [config['url']]
        
        # Se tem paginação, adicionar mais páginas
        if config.get('paginacao'):
            for pagina in range(2, config.get('max_paginas', 5) + 1):
                urls_para_buscar.append(config['url_pagina'].format(pagina=pagina))
        
        for url in urls_para_buscar:
            try:
                print(f"🔍 Acessando: {config['nome']} - {url}")
                response = requests.get(url, headers=headers, timeout=20)
                
                if response.status_code != 200:
                    print(f"   ❌ HTTP {response.status_code}")
                    if url != config['url']:
                        break  # Para paginação se der erro
                    continue
                
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Buscar links de imóveis (padrão adaptado para Andi)
                links = soup.find_all('a', href=re.compile(r'/imovel|/Imovel|/imoveis|/comprar|/detalhes|/property', re.I))
                
                # Buscar cards
                cards = soup.find_all(['div', 'article', 'li', 'section'], 
                                     class_=re.compile(r'card|imovel|property|listing|item|box|result|anuncio|post', re.I))
                
                # Buscar preços e áreas no texto
                texto_completo = soup.get_text()
                precos_texto = re.findall(r'R\$\s*[\d.,]+', texto_completo)
                areas_texto = re.findall(r'(\d+[\.,]?\d*)\s*m²', texto_completo)
                
                print(f"   Links: {len(links)} | Cards: {len(cards)} | Preços: {len(precos_texto)} | Áreas: {len(areas_texto)}")
                
                imoveis_pagina = []
                
                # Processar links encontrados
                if links:
                    for link in links:
                        try:
                            href = link.get('href', '')
                            texto = link.get_text(strip=True)
                            
                            if len(texto) < 10:
                                for parent_tag in ['div', 'article', 'li', 'section']:
                                    pai = link.find_parent(parent_tag)
                                    if pai:
                                        texto = pai.get_text(strip=True)
                                        if len(texto) > 20:
                                            break
                            
                            tipo_imovel = 'Terreno' if 'terreno' in href.lower() + texto.lower() else 'Casa'
                            
                            if tipo and tipo.lower() not in tipo_imovel.lower():
                                continue
                            
                            area = 0
                            area_match = re.search(r'(\d+[\.,]?\d*)\s*m²', texto)
                            if area_match:
                                area = float(area_match.group(1).replace(',', '.'))
                            
                            preco = 0
                            preco_match = re.search(r'R\$\s*([\d.]+(?:,\d{2})?)', texto)
                            if preco_match:
                                preco_str = preco_match.group(1).replace('.', '').replace(',', '.')
                                preco = float(preco_str)
                            
                            if 'aluguel' in texto.lower() and 'venda' not in texto.lower():
                                continue
                            
                            if preco > 0 and (preco < preco_min or preco > preco_max):
                                continue
                            if area > 0 and (area < area_min or area > area_max):
                                continue
                            
                            link_completo = config['url_base'] + href if href.startswith('/') else href
                            if not link_completo.startswith('http'):
                                link_completo = url
                            
                            preco_m2 = round(preco / area, 2) if preco > 0 and area > 0 else 0
                            
                            imoveis_pagina.append({
                                'codigo': '',
                                'titulo': texto[:150] or f'{tipo_imovel} - {config["nome"]}',
                                'tipo': tipo_imovel,
                                'preco': preco,
                                'area': area,
                                'preco_m2': preco_m2,
                                'quartos': 0,
                                'banheiros': 0,
                                'vagas': 0,
                                'link': link_completo,
                                'imobiliaria': config['nome'],
                                'telefone': config['telefone'],
                                'cor': config['cor']
                            })
                        except:
                            continue
                
                # Se não achou links, processar cards
                if not imoveis_pagina and cards:
                    for card in cards:
                        try:
                            texto = card.get_text(strip=True)
                            
                            tipo_imovel = 'Terreno' if 'terreno' in texto.lower() else 'Casa'
                            if tipo and tipo.lower() not in tipo_imovel.lower():
                                continue
                            
                            area = 0
                            area_match = re.search(r'(\d+[\.,]?\d*)\s*m²', texto)
                            if area_match:
                                area = float(area_match.group(1).replace(',', '.'))
                            
                            preco = 0
                            preco_match = re.search(r'R\$\s*([\d.]+(?:,\d{2})?)', texto)
                            if preco_match:
                                preco = float(preco_match.group(1).replace('.', '').replace(',', '.'))
                            
                            if preco <= 0:
                                continue
                            
                            link_elem = card.find('a', href=True)
                            link_completo = config['url_base'] + link_elem['href'] if link_elem and link_elem['href'].startswith('/') else (link_elem['href'] if link_elem else url)
                            
                            preco_m2 = round(preco / area, 2) if area > 0 else 0
                            
                            imoveis_pagina.append({
                                'codigo': '',
                                'titulo': texto[:150],
                                'tipo': tipo_imovel,
                                'preco': preco,
                                'area': area,
                                'preco_m2': preco_m2,
                                'quartos': 0,
                                'banheiros': 0,
                                'vagas': 0,
                                'link': link_completo,
                                'imobiliaria': config['nome'],
                                'telefone': config['telefone'],
                                'cor': config['cor']
                            })
                        except:
                            continue
                
                # Se ainda não achou, usar preços do texto
                if not imoveis_pagina and precos_texto and areas_texto:
                    for i in range(min(len(precos_texto), len(areas_texto))):
                        try:
                            preco = float(re.sub(r'[^\d]', '', precos_texto[i]))
                            area = float(areas_texto[i].replace(',', '.'))
                            
                            if area > 0 and preco > 0:
                                imoveis_pagina.append({
                                    'codigo': '',
                                    'titulo': f'Imóvel {i+1} - {config["nome"]}',
                                    'tipo': tipo or 'Casa/Terreno',
                                    'preco': preco,
                                    'area': area,
                                    'preco_m2': round(preco / area, 2),
                                    'quartos': 0,
                                    'banheiros': 0,
                                    'vagas': 0,
                                    'link': url,
                                    'imobiliaria': config['nome'],
                                    'telefone': config['telefone'],
                                    'cor': config['cor']
                                })
                        except:
                            continue
                
                print(f"   ✅ {len(imoveis_pagina)} imóveis nesta página")
                todos_imoveis.extend(imoveis_pagina)
                
                # Se não encontrou nada nesta página, para paginação
                if not imoveis_pagina and url != config['url']:
                    break
                    
            except Exception as e:
                print(f"   ❌ Erro: {str(e)[:100]}")
                if url != config['url']:
                    break
        
        return todos_imoveis
    
    def buscar(self, imob='todas', tipo=None, pmin=0, pmax=999999999, amin=0, amax=999999):
        """Busca em uma ou todas as imobiliárias"""
        todos = []
        for key, cfg in self.imobiliarias.items():
            if imob == 'todas' or imob == key:
                print(f"\n🔍 Buscando: {cfg['nome']}...")
                imoveis = self.buscar_site(cfg, tipo, pmin, pmax, amin, amax)
                todos.extend(imoveis)
                print(f"   {cfg['nome']}: {len(imoveis)} imóveis")
        
        # Remover duplicados
        links_vistos = set()
        unicos = []
        for i in todos:
            if i['link'] not in links_vistos:
                links_vistos.add(i['link'])
                unicos.append(i)
        
        self.imoveis_encontrados = sorted(unicos, key=lambda x: x['preco_m2'] if x['preco_m2'] > 0 else 999999)
        
        # Análise
        validos = [i for i in self.imoveis_encontrados if i['preco_m2'] > 0]
        analise = None
        if validos:
            precos = sorted([i['preco_m2'] for i in validos])
            n = len(precos)
            mediana = precos[n//2] if n%2 else (precos[n//2-1]+precos[n//2])/2
            
            por_imob = {}
            for i in validos:
                imob_nome = i['imobiliaria']
                if imob_nome not in por_imob:
                    por_imob[imob_nome] = {'total':0, 'precos':[], 'cor':i['cor']}
                por_imob[imob_nome]['total'] += 1
                por_imob[imob_nome]['precos'].append(i['preco_m2'])
            
            resumo = {}
            for imob_nome, dados in por_imob.items():
                if dados['precos']:
                    p = sorted(dados['precos'])
                    np_p = len(p)
                    resumo[imob_nome] = {
                        'total': dados['total'],
                        'media': round(sum(p)/np_p, 2),
                        'mediana': round(p[np_p//2], 2) if np_p%2 else round((p[np_p//2-1]+p[np_p//2])/2, 2),
                        'cor': dados['cor']
                    }
            
            analise = {
                'total': len(validos),
                'media': round(sum(precos)/n, 2),
                'mediana': round(mediana, 2),
                'minimo': round(min(precos), 2),
                'maximo': round(max(precos), 2),
                'q1': round(precos[n//4] if n>=4 else precos[0], 2),
                'q3': round(precos[3*n//4] if n>=4 else precos[-1], 2),
                'por_imobiliaria': resumo
            }
        
        return self.imoveis_encontrados, analise

precificador = PrecificadorRecantoDoVale()

@app.route('/')
def index():
    return '''
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Precificador - Sapucaia do Sul</title>
    <style>
        *{margin:0;padding:0;box-sizing:border-box}
        body{font-family:system-ui,sans-serif;background:#0d1117;color:#c9d1d9;min-height:100vh}
        .container{max-width:1000px;margin:0 auto;padding:20px}
        .header{text-align:center;padding:30px;background:#161b22;border-radius:15px;margin-bottom:25px;border:1px solid #30363d}
        .header h1{font-size:2em;margin-bottom:8px;color:#58a6ff}
        .header .loc{color:#3fb950}
        .badges{display:flex;justify-content:center;gap:10px;margin-top:12px;flex-wrap:wrap}
        .badge{padding:5px 12px;border-radius:20px;font-size:.75em}
        .card{background:#161b22;border-radius:15px;padding:25px;margin-bottom:20px;border:1px solid #30363d}
        .card h2{color:#58a6ff;margin-bottom:15px;font-size:1.2em}
        .grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px}
        .field{margin-bottom:10px}
        .field label{display:block;color:#8b949e;margin-bottom:5px;font-size:.85em}
        .field input,.field select{width:100%;padding:10px;border:1px solid #30363d;border-radius:8px;background:#0d1117;color:#c9d1d9;font-size:.95em}
        .btn{display:block;width:100%;padding:14px;background:#238636;color:#fff;border:none;border-radius:8px;font-size:1em;cursor:pointer;font-weight:bold;margin-top:15px;transition:.2s}
        .btn:hover{background:#2ea043}
        .loading{display:none;text-align:center;padding:25px;color:#58a6ff}
        .loading.show{display:block}
        .spinner{border:3px solid #30363d;border-top:3px solid #58a6ff;border-radius:50%;width:35px;height:35px;animation:spin 1s linear infinite;margin:0 auto 15px}
        @keyframes spin{to{transform:rotate(360deg)}}
        .stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:10px;margin-bottom:15px}
        .stat{background:#0d1117;padding:15px;border-radius:10px;text-align:center;border:1px solid #30363d}
        .stat .val{font-size:1.4em;font-weight:bold;color:#3fb950}
        .stat .lbl{color:#8b949e;font-size:.75em;margin-top:4px}
        table{width:100%;border-collapse:collapse;font-size:.85em}
        th{background:#1a1f2b;padding:10px;text-align:left;color:#58a6ff;font-weight:600}
        td{padding:8px 10px;border-bottom:1px solid #21262d}
        tr:hover{background:#1a1f2b}
        .link{color:#58a6ff;text-decoration:none}
        .link:hover{text-decoration:underline}
        .tipo-casa{color:#3fb950}.tipo-terreno{color:#d2991d}
        .guia{background:#0d1117;border:1px solid #238636;border-radius:10px;padding:15px;margin-top:15px}
        .guia h3{color:#3fb950;margin-bottom:10px}
        .guia-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:10px}
        .guia-item{text-align:center;padding:10px}
        .guia-item .preco{font-size:1.2em;font-weight:bold;color:#c9d1d9}
        .guia-item .area{color:#8b949e;font-size:.8em}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Precificador de Imoveis</h1>
            <p class="loc">Sapucaia do Sul/RS</p>
            <div class="badges">
                <span class="badge" style="background:rgba(33,150,243,0.15);color:#58a6ff">Besser</span>
                <span class="badge" style="background:rgba(156,39,176,0.15);color:#bc8cff">Corretor e Cia</span>
                <span class="badge" style="background:rgba(255,87,34,0.15);color:#f78166">Sauthier</span>
                <span class="badge" style="background:rgba(0,188,212,0.15);color:#00BCD4">Imob. Sapucaia</span>
                <span class="badge" style="background:rgba(233,30,99,0.15);color:#E91E63">Andi Imóveis</span>
            </div>
        </div>
        
        <div class="card">
            <h2>Filtros</h2>
            <div class="grid">
                <div class="field">
                    <label>Imobiliaria</label>
                    <select id="imob">
                        <option value="todas">TODAS (5 imobiliarias)</option>
                        <option value="besser">Besser</option>
                        <option value="corretorcia">Corretor e Cia</option>
                        <option value="sauthier">Sauthier</option>
                        <option value="sapucaia">Imob. Sapucaia</option>
                        <option value="andi">Andi Imóveis</option>
                    </select>
                </div>
                <div class="field">
                    <label>Tipo</label>
                    <select id="tipo">
                        <option value="">Todos</option>
                        <option value="Casa">Casas</option>
                        <option value="Terreno">Terrenos</option>
                    </select>
                </div>
                <div class="field">
                    <label>Preco Min (R$)</label>
                    <input type="number" id="pmin" placeholder="150000">
                </div>
                <div class="field">
                    <label>Preco Max (R$)</label>
                    <input type="number" id="pmax" placeholder="600000">
                </div>
                <div class="field">
                    <label>Area Min (m²)</label>
                    <input type="number" id="amin" placeholder="50">
                </div>
                <div class="field">
                    <label>Area Max (m²)</label>
                    <input type="number" id="amax" placeholder="300">
                </div>
            </div>
            <button class="btn" onclick="buscar()">Buscar Imoveis</button>
        </div>
        
        <div class="loading" id="loading">
            <div class="spinner"></div>
            <p>Buscando imoveis nas 5 imobiliarias...</p>
        </div>
        
        <div id="resultados"></div>
    </div>
    
    <script>
        function fmoney(v){return v>0?'R$ '+v.toLocaleString('pt-BR',{minimumFractionDigits:2}):'N/D'}
        
        async function buscar(){
            document.getElementById('loading').classList.add('show');
            document.getElementById('resultados').innerHTML='';
            
            const p=new URLSearchParams({
                imob:document.getElementById('imob').value,
                tipo:document.getElementById('tipo').value,
                pmin:document.getElementById('pmin').value||0,
                pmax:document.getElementById('pmax').value||999999999,
                amin:document.getElementById('amin').value||0,
                amax:document.getElementById('amax').value||999999
            });
            
            try{
                const r=await fetch('/buscar?'+p);
                const d=await r.json();
                mostrar(d);
            }catch(e){
                document.getElementById('resultados').innerHTML='<div class="card"><p style="color:#f85149">Erro: '+e.message+'</p></div>';
            }finally{
                document.getElementById('loading').classList.remove('show');
            }
        }
        
        function mostrar(d){
            if(!d.analise||d.analise.total===0){
                document.getElementById('resultados').innerHTML='<div class="card"><p>Nenhum imovel encontrado.</p></div>';
                return;
            }
            const a=d.analise;
            
            let h='<div class="card"><h2>Analise</h2><div class="stats">';
            h+=`<div class="stat"><div class="val">${a.total}</div><div class="lbl">Total</div></div>`;
            h+=`<div class="stat"><div class="val">R$ ${a.mediana.toLocaleString('pt-BR')}</div><div class="lbl">Mediana/m²</div></div>`;
            h+=`<div class="stat"><div class="val">R$ ${a.q1.toLocaleString('pt-BR')}</div><div class="lbl">Q1 (25%)</div></div>`;
            h+=`<div class="stat"><div class="val">R$ ${a.q3.toLocaleString('pt-BR')}</div><div class="lbl">Q3 (75%)</div></div>`;
            h+=`<div class="stat"><div class="val">R$ ${a.minimo.toLocaleString('pt-BR')}</div><div class="lbl">Minimo</div></div>`;
            h+=`<div class="stat"><div class="val">R$ ${a.maximo.toLocaleString('pt-BR')}</div><div class="lbl">Maximo</div></div>`;
            h+='</div>';
            
            if(a.por_imobiliaria){
                h+='<div class="stats">';
                for(const[im,dados]of Object.entries(a.por_imobiliaria)){
                    h+=`<div class="stat" style="border-left:3px solid ${dados.cor}"><div class="val" style="color:${dados.cor}">${dados.total}</div><div class="lbl">${im}</div><div class="lbl">Med: R$ ${dados.mediana.toLocaleString('pt-BR')}/m²</div></div>`;
                }
                h+='</div>';
            }
            
            h+=`<div class="guia"><h3>Guia de Precificacao (mediana: R$ ${a.mediana.toLocaleString('pt-BR')}/m²)</h3><div class="guia-grid">`;
            [50,100,150,200].forEach(m2=>{
                h+=`<div class="guia-item"><div class="area">${m2} m²</div><div class="preco">${fmoney(m2*a.mediana)}</div></div>`;
            });
            h+='</div></div></div>';
            
            h+='<div class="card"><h2>Imoveis</h2><table><thead><tr><th>#</th><th>Tipo</th><th>Imobiliaria</th><th>Preco</th><th>Area</th><th>/m²</th><th>Link</th></tr></thead><tbody>';
            
            d.imoveis.forEach((im,i)=>{
                h+=`<tr><td>${i+1}</td><td class="${im.tipo==='Casa'?'tipo-casa':'tipo-terreno'}">${im.tipo}</td><td style="color:${im.cor}">${im.imobiliaria}</td><td>${fmoney(im.preco)}</td><td>${im.area>0?im.area.toFixed(1)+'m²':'N/D'}</td><td><strong>${im.preco_m2>0?'R$ '+im.preco_m2.toLocaleString('pt-BR'):'N/D'}</strong></td><td><a href="${im.link}" target="_blank" class="link">Ver</a></td></tr>`;
            });
            
            h+='</tbody></table></div>';
            document.getElementById('resultados').innerHTML=h;
        }
    </script>
</body>
</html>'''

@app.route('/buscar')
def buscar():
    imob = request.args.get('imob', 'todas')
    tipo = request.args.get('tipo', '')
    pmin = float(request.args.get('pmin', 0))
    pmax = float(request.args.get('pmax', 999999999))
    amin = float(request.args.get('amin', 0))
    amax = float(request.args.get('amax', 999999))
    
    imoveis, analise = precificador.buscar(imob, tipo if tipo else None, pmin, pmax, amin, amax)
    
    return jsonify({'imoveis': imoveis, 'analise': analise})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)