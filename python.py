# app.py - Precificador de Imóveis - Recanto do Vale
# Imobiliárias: Besser, Corretor e Cia, Sauthier

from flask import Flask, request, jsonify
import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
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
                'padrao_link': r'/imovel/(casa|terreno)-sapucaia-do-sul',
                'telefone': '(51) 3459-2222',
                'cor': '#2196F3'
            },
            'corretorcia': {
                'nome': 'Corretor e Cia',
                'url': 'https://www.corretorecia.com/imobiliaria/venda/casa/recanto-do-vale/sapucaia-do-sul-rs/imoveis/',
                'url_base': 'https://www.corretorecia.com',
                'padrao_link': r'/imovel/',
                'telefone': '(51) 3474-1212',
                'cor': '#9C27B0'
            },
            'sauthier': {
                'nome': 'Sauthier Imóveis',
                'url': 'https://www.sauthier.com.br/Imovel/Venda/Casa/Vargas/Sapucaia-Do-Sul/RS/',
                'url_base': 'https://www.sauthier.com.br',
                'padrao_link': r'/Imovel/|/imovel/',
                'telefone': '(51) 3474-1111',
                'cor': '#FF5722'
            }
        }
        
    def buscar_site(self, config, tipo=None, preco_min=0, preco_max=999999999, area_min=0, area_max=999999):
        """Busca imóveis em um site específico"""
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'pt-BR,pt;q=0.9',
        }
        
        try:
            print(f"🔍 Acessando: {config['nome']} - {config['url']}")
            response = requests.get(config['url'], headers=headers, timeout=20)
            
            if response.status_code != 200:
                print(f"   ❌ HTTP {response.status_code}")
                return []
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Buscar links de imóveis
            links = soup.find_all('a', href=re.compile(config['padrao_link'], re.I))
            
            # Buscar cards
            cards = soup.find_all(['div', 'article', 'li', 'section'], 
                                 class_=re.compile(r'card|imovel|property|listing|item|box|result', re.I))
            
            # Buscar preços e áreas no texto
            texto_completo = soup.get_text()
            precos_texto = re.findall(r'R\$\s*[\d.,]+', texto_completo)
            areas_texto = re.findall(r'(\d+[\.,]?\d*)\s*m²', texto_completo)
            
            print(f"   Links: {len(links)} | Cards: {len(cards)} | Preços: {len(precos_texto)} | Áreas: {len(areas_texto)}")
            
            imoveis = []
            
            # Processar links encontrados
            if links:
                for link in links:
                    try:
                        href = link.get('href', '')
                        texto = link.get_text(strip=True)
                        
                        # Se o link tem pouco texto, pegar do elemento pai
                        if len(texto) < 10:
                            for parent_tag in ['div', 'article', 'li', 'section']:
                                pai = link.find_parent(parent_tag)
                                if pai:
                                    texto = pai.get_text(strip=True)
                                    if len(texto) > 20:
                                        break
                        
                        # Identificar tipo
                        tipo_imovel = 'Terreno' if 'terreno' in href.lower() + texto.lower() else 'Casa'
                        
                        # Filtrar por tipo
                        if tipo and tipo.lower() not in tipo_imovel.lower():
                            continue
                        
                        # Extrair área
                        area = 0
                        area_match = re.search(r'(\d+[\.,]?\d*)\s*m²', texto)
                        if area_match:
                            area = float(area_match.group(1).replace(',', '.'))
                        
                        # Extrair preço
                        preco = 0
                        preco_match = re.search(r'R\$\s*([\d.]+(?:,\d{2})?)', texto)
                        if preco_match:
                            preco_str = preco_match.group(1).replace('.', '').replace(',', '.')
                            preco = float(preco_str)
                        
                        # Ignorar aluguel
                        if 'aluguel' in texto.lower() and 'venda' not in texto.lower():
                            continue
                        
                        # Aplicar filtros
                        if preco > 0 and (preco < preco_min or preco > preco_max):
                            continue
                        if area > 0 and (area < area_min or area > area_max):
                            continue
                        
                        # Montar link completo
                        link_completo = config['url_base'] + href if href.startswith('/') else href
                        if not link_completo.startswith('http'):
                            link_completo = config['url']
                        
                        # Extrair detalhes
                        quartos = 0
                        q_match = re.search(r'(\d+)\s*Quartos?|(\d+)\s*Dormitórios?', texto)
                        if q_match:
                            quartos = int(q_match.group(1) or q_match.group(2))
                        
                        banheiros = 0
                        b_match = re.search(r'(\d+)\s*Banheiros?|(\d+)\s*Suítes?', texto)
                        if b_match:
                            banheiros = int(b_match.group(1) or b_match.group(2))
                        
                        vagas = 0
                        v_match = re.search(r'(\d+)\s*Vagas?', texto)
                        if v_match:
                            vagas = int(v_match.group(1))
                        
                        # Código do imóvel
                        codigo = ""
                        cod_match = re.search(r'(CA\d+-ESUU|TE\d+-ESUU|\d{4,})', texto)
                        if cod_match:
                            codigo = cod_match.group(1)
                        
                        # Calcular preço/m²
                        preco_m2 = round(preco / area, 2) if preco > 0 and area > 0 else 0
                        
                        imoveis.append({
                            'codigo': codigo,
                            'titulo': texto[:150] or f'{tipo_imovel} - {config["nome"]}',
                            'tipo': tipo_imovel,
                            'preco': preco,
                            'area': area,
                            'preco_m2': preco_m2,
                            'quartos': quartos,
                            'banheiros': banheiros,
                            'vagas': vagas,
                            'link': link_completo,
                            'imobiliaria': config['nome'],
                            'telefone': config['telefone'],
                            'cor': config['cor']
                        })
                    except Exception as e:
                        continue
            
            # Se não achou links, processar cards
            if not imoveis and cards:
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
                        link_completo = config['url_base'] + link_elem['href'] if link_elem and link_elem['href'].startswith('/') else (link_elem['href'] if link_elem else config['url'])
                        
                        preco_m2 = round(preco / area, 2) if area > 0 else 0
                        
                        imoveis.append({
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
            if not imoveis and precos_texto and areas_texto:
                for i in range(min(len(precos_texto), len(areas_texto))):
                    try:
                        preco = float(re.sub(r'[^\d]', '', precos_texto[i]))
                        area = float(areas_texto[i].replace(',', '.'))
                        
                        if area > 0 and preco > 0:
                            imoveis.append({
                                'codigo': '',
                                'titulo': f'Imóvel {i+1} - {config["nome"]}',
                                'tipo': tipo or 'Casa/Terreno',
                                'preco': preco,
                                'area': area,
                                'preco_m2': round(preco / area, 2),
                                'quartos': 0,
                                'banheiros': 0,
                                'vagas': 0,
                                'link': config['url'],
                                'imobiliaria': config['nome'],
                                'telefone': config['telefone'],
                                'cor': config['cor']
                            })
                    except:
                        continue
            
            print(f"   ✅ {len(imoveis)} imóveis extraídos")
            return imoveis
            
        except Exception as e:
            print(f"   ❌ Erro {config['nome']}: {str(e)[:100]}")
            return []
    
    def buscar_imoveis(self, imobiliaria='todas', tipo=None, preco_min=0, preco_max=999999999, area_min=0, area_max=999999):
        """Busca em uma ou todas as imobiliárias"""
        todos_imoveis = []
        
        for key, config in self.imobiliarias.items():
            if imobiliaria == 'todas' or imobiliaria == key:
                print(f"\n🔍 Buscando: {config['nome']}...")
                imoveis = self.buscar_site(config, tipo, preco_min, preco_max, area_min, area_max)
                todos_imoveis.extend(imoveis)
                print(f"   {config['nome']}: {len(imoveis)} imóveis")
        
        # Remover duplicados
        links_vistos = set()
        unicos = []
        for i in todos_imoveis:
            if i['link'] not in links_vistos:
                links_vistos.add(i['link'])
                unicos.append(i)
        
        # Ordenar por preço/m²
        self.imoveis_encontrados = sorted(unicos, key=lambda x: x['preco_m2'] if x['preco_m2'] > 0 else 999999)
        return self.imoveis_encontrados
    
    def analisar(self):
        """Análise de precificação"""
        validos = [i for i in self.imoveis_encontrados if i['preco_m2'] > 0]
        if not validos:
            return None
        
        precos = sorted([i['preco_m2'] for i in validos])
        n = len(precos)
        
        # Mediana
        if n % 2 == 0:
            mediana = (precos[n//2 - 1] + precos[n//2]) / 2
        else:
            mediana = precos[n//2]
        
        # Por imobiliária
        por_imobiliaria = {}
        for i in validos:
            imob = i.get('imobiliaria', 'Desconhecida')
            if imob not in por_imobiliaria:
                por_imobiliaria[imob] = {'total': 0, 'precos': [], 'cor': i.get('cor', '#666')}
            por_imobiliaria[imob]['total'] += 1
            por_imobiliaria[imob]['precos'].append(i['preco_m2'])
        
        resumo_imob = {}
        for imob, dados in por_imobiliaria.items():
            if dados['precos']:
                p = sorted(dados['precos'])
                np_p = len(p)
                resumo_imob[imob] = {
                    'total': dados['total'],
                    'media': round(sum(p) / np_p, 2),
                    'mediana': round(p[np_p//2], 2) if np_p % 2 else round((p[np_p//2-1] + p[np_p//2]) / 2, 2),
                    'minimo': round(min(p), 2),
                    'maximo': round(max(p), 2),
                    'cor': dados['cor']
                }
        
        return {
            'total': len(validos),
            'casas': len([i for i in validos if i['tipo'] == 'Casa']),
            'terrenos': len([i for i in validos if i['tipo'] == 'Terreno']),
            'media': round(sum(precos) / n, 2),
            'mediana': round(mediana, 2),
            'minimo': round(min(precos), 2),
            'maximo': round(max(precos), 2),
            'q1': round(precos[n//4] if n >= 4 else precos[0], 2),
            'q3': round(precos[3*n//4] if n >= 4 else precos[-1], 2),
            'por_imobiliaria': resumo_imob
        }

precificador = PrecificadorRecantoDoVale()

@app.route('/')
def index():
    return '''
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🏠 Precificador - Recanto do Vale</title>
    <style>
        *{margin:0;padding:0;box-sizing:border-box}
        body{font-family:'Segoe UI',Tahoma,Geneva,Verdana,sans-serif;background:linear-gradient(135deg,#1a1a2e 0%,#16213e 50%,#0f3460 100%);min-height:100vh;color:#fff}
        .container{max-width:1200px;margin:0 auto;padding:20px}
        .header{text-align:center;padding:30px 0;background:rgba(255,255,255,0.05);border-radius:20px;margin-bottom:30px}
        .header h1{font-size:2.5em;margin-bottom:10px}
        .header p{color:#a0a0a0;font-size:1.1em}
        .header .location{color:#4CAF50;font-weight:bold}
        .badges{display:flex;justify-content:center;gap:15px;margin-top:15px;flex-wrap:wrap}
        .badge{padding:5px 15px;border-radius:20px;font-size:.85em}
        .card{background:rgba(255,255,255,0.08);border-radius:15px;padding:25px;margin-bottom:20px;border:1px solid rgba(255,255,255,0.1)}
        .card h2{font-size:1.3em;margin-bottom:20px;color:#4CAF50;border-bottom:2px solid rgba(76,175,80,0.3);padding-bottom:10px}
        .grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:15px}
        .field{margin-bottom:15px}
        .field label{display:block;margin-bottom:5px;color:#ccc;font-size:.9em}
        .field input,.field select{width:100%;padding:10px;border:1px solid rgba(255,255,255,0.2);border-radius:8px;background:rgba(255,255,255,0.1);color:#fff;font-size:1em}
        .field select option{background:#1a1a2e;color:#fff}
        .btn{padding:12px 30px;border:none;border-radius:8px;font-size:1.1em;cursor:pointer;font-weight:bold;transition:all .3s;margin:5px}
        .btn-primary{background:linear-gradient(135deg,#4CAF50,#45a049);color:#fff}
        .btn-primary:hover{transform:translateY(-2px);box-shadow:0 5px 20px rgba(76,175,80,0.4)}
        .btn-secondary{background:rgba(255,255,255,0.1);color:#fff}
        .loading{display:none;text-align:center;padding:20px}
        .loading.show{display:block}
        .spinner{border:4px solid rgba(255,255,255,0.1);border-top:4px solid #4CAF50;border-radius:50%;width:40px;height:40px;animation:spin 1s linear infinite;margin:0 auto 15px}
        @keyframes spin{to{transform:rotate(360deg)}}
        .resultados{display:none}
        .resultados.show{display:block}
        .stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:15px;margin-bottom:20px}
        .stat{background:rgba(255,255,255,0.05);padding:15px;border-radius:10px;text-align:center;border:1px solid rgba(255,255,255,0.1)}
        .stat .val{font-size:1.5em;font-weight:bold;color:#4CAF50}
        .stat .lbl{color:#aaa;font-size:.8em;margin-top:5px}
        .imobs{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:15px;margin-bottom:20px}
        .imob-card{background:rgba(255,255,255,0.05);padding:15px;border-radius:10px;border-left:4px solid #666}
        .imob-card h4{margin-bottom:10px}
        .imob-card .info{color:#ccc;font-size:.9em}
        table{width:100%;border-collapse:collapse;margin-top:15px;font-size:.9em}
        th{background:rgba(76,175,80,0.2);padding:12px;text-align:left;color:#4CAF50}
        td{padding:10px 12px;border-bottom:1px solid rgba(255,255,255,0.05)}
        tr:hover{background:rgba(255,255,255,0.05)}
        .link{color:#4CAF50;text-decoration:none}
        .tipo-badge{padding:3px 10px;border-radius:12px;font-size:.8em;font-weight:bold}
        .tipo-casa{background:rgba(76,175,80,0.2);color:#4CAF50}
        .tipo-terreno{background:rgba(255,152,0,0.2);color:#FF9800}
        .guia{background:rgba(76,175,80,0.1);border:1px solid rgba(76,175,80,0.3);border-radius:15px;padding:20px;margin-top:20px}
        .guia h3{color:#4CAF50;margin-bottom:15px}
        .guia-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:10px}
        .guia-item{background:rgba(0,0,0,0.3);padding:15px;border-radius:10px;text-align:center}
        .guia-item .preco{font-size:1.3em;font-weight:bold}
        .guia-item .area{color:#aaa;font-size:.9em}
        .footer{text-align:center;padding:20px;color:#666;font-size:.9em}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🏠 Precificador de Imóveis</h1>
            <p>📍 <span class="location">Recanto do Vale - Sapucaia do Sul/RS</span></p>
            <div class="badges">
                <span class="badge" style="background:rgba(33,150,243,0.2);color:#2196F3">🏢 Besser</span>
                <span class="badge" style="background:rgba(156,39,176,0.2);color:#9C27B0">🏢 Corretor e Cia</span>
                <span class="badge" style="background:rgba(255,87,34,0.2);color:#FF5722">🏢 Sauthier</span>
            </div>
        </div>
        
        <div class="card">
            <h2>🔍 Filtros de Busca</h2>
            <div class="grid">
                <div class="field">
                    <label>🏢 Imobiliária</label>
                    <select id="imob">
                        <option value="todas">📋 TODAS (3 imobiliárias)</option>
                        <option value="besser">🏢 Besser</option>
                        <option value="corretorcia">🏢 Corretor e Cia</option>
                        <option value="sauthier">🏢 Sauthier</option>
                    </select>
                </div>
                <div class="field">
                    <label>🏷️ Tipo</label>
                    <select id="tipo">
                        <option value="">📋 Todos</option>
                        <option value="Casa">🏠 Casas</option>
                        <option value="Terreno">🏗️ Terrenos</option>
                    </select>
                </div>
                <div class="field">
                    <label>💰 Preço Mín (R$)</label>
                    <input type="number" id="pmin" placeholder="100000">
                </div>
                <div class="field">
                    <label>💰 Preço Máx (R$)</label>
                    <input type="number" id="pmax" placeholder="600000">
                </div>
                <div class="field">
                    <label>📐 Área Mín (m²)</label>
                    <input type="number" id="amin" placeholder="50">
                </div>
                <div class="field">
                    <label>📐 Área Máx (m²)</label>
                    <input type="number" id="amax" placeholder="300">
                </div>
            </div>
            <div style="text-align:center;margin-top:20px">
                <button class="btn btn-primary" onclick="buscar()">🔍 Buscar Imóveis</button>
                <button class="btn btn-secondary" onclick="limpar()">🔄 Limpar</button>
            </div>
        </div>
        
        <div class="loading" id="loading">
            <div class="spinner"></div>
            <p>🔍 Buscando imóveis nas imobiliárias...</p>
            <p style="color:#aaa;font-size:.9em">Isso pode levar alguns segundos</p>
        </div>
        
        <div class="resultados" id="resultados"></div>
        
        <div class="footer">
            <p>🏢 Besser + Corretor e Cia + Sauthier | Dados em tempo real</p>
        </div>
    </div>
    
    <script>
        function fmoney(v){return v>0?'R$ '+v.toLocaleString('pt-BR',{minimumFractionDigits:2}):'N/D'}
        
        async function buscar(){
            document.getElementById('loading').classList.add('show');
            document.getElementById('resultados').classList.remove('show');
            
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
                alert('Erro: '+e.message);
            }finally{
                document.getElementById('loading').classList.remove('show');
                document.getElementById('resultados').classList.add('show');
            }
        }
        
        function mostrar(d){
            const div=document.getElementById('resultados');
            if(!d.analise||d.analise.total===0){
                div.innerHTML='<div class="card"><p>❌ Nenhum imóvel encontrado com esses filtros.</p></div>';
                return;
            }
            const a=d.analise;
            
            let h='<div class="card"><h2>📊 Análise</h2><div class="stats">';
            h+=`<div class="stat"><div class="val">${a.total}</div><div class="lbl">Total</div></div>`;
            h+=`<div class="stat"><div class="val">R$ ${a.mediana.toLocaleString('pt-BR')}</div><div class="lbl">⭐ Mediana/m²</div></div>`;
            h+=`<div class="stat"><div class="val">R$ ${a.q1.toLocaleString('pt-BR')}</div><div class="lbl">Q1 (25%)</div></div>`;
            h+=`<div class="stat"><div class="val">R$ ${a.q3.toLocaleString('pt-BR')}</div><div class="lbl">Q3 (75%)</div></div>`;
            h+=`<div class="stat"><div class="val">R$ ${a.minimo.toLocaleString('pt-BR')}</div><div class="lbl">Mínimo</div></div>`;
            h+=`<div class="stat"><div class="val">R$ ${a.maximo.toLocaleString('pt-BR')}</div><div class="lbl">Máximo</div></div>`;
            h+='</div>';
            
            if(a.por_imobiliaria){
                h+='<h3 style="color:#4CAF50;margin-top:20px">🏢 Por Imobiliária</h3><div class="imobs">';
                for(const[imob,dados]of Object.entries(a.por_imobiliaria)){
                    h+=`<div class="imob-card" style="border-left-color:${dados.cor||'#666'}"><h4 style="color:${dados.cor||'#fff'}">${imob}</h4><div class="info"><p>📋 ${dados.total} imóveis</p><p>⭐ Med: R$ ${dados.mediana.toLocaleString('pt-BR')}/m²</p><p>📊 Média: R$ ${dados.media.toLocaleString('pt-BR')}/m²</p></div></div>`;
                }
                h+='</div>';
            }
            
            h+=`<div class="guia"><h3>💡 Guia (mediana: R$ ${a.mediana.toLocaleString('pt-BR')}/m²)</h3><div class="guia-grid">
                <div class="guia-item"><div style="color:#4CAF50">🟢 50m²</div><div class="preco">${fmoney(50*a.mediana)}</div></div>
                <div class="guia-item"><div style="color:#FFC107">🟡 100m²</div><div class="preco">${fmoney(100*a.mediana)}</div></div>
                <div class="guia-item"><div style="color:#FF9800">🟠 150m²</div><div class="preco">${fmoney(150*a.mediana)}</div></div>
                <div class="guia-item"><div style="color:#f44336">🔴 200m²</div><div class="preco">${fmoney(200*a.mediana)}</div></div>
            </div></div></div>`;
            
            h+='<div class="card"><h2>📋 Imóveis</h2><div style="overflow-x:auto"><table><thead><tr><th>#</th><th>Tipo</th><th>Imobiliária</th><th>Preço</th><th>Área</th><th>⭐/m²</th><th>Link</th></tr></thead><tbody>';
            
            d.imoveis.forEach((im,i)=>{
                const tb=im.tipo==='Casa'?'tipo-casa':'tipo-terreno';
                h+=`<tr><td>${i+1}</td><td><span class="tipo-badge ${tb}">${im.tipo}</span></td><td style="color:${im.cor||'#fff'}">${im.imobiliaria||'N/D'}</td><td>${fmoney(im.preco)}</td><td>${im.area>0?im.area.toFixed(1)+'m²':'N/D'}</td><td><strong>${im.preco_m2>0?'R$ '+im.preco_m2.toLocaleString('pt-BR')+'/m²':'N/D'}</strong></td><td><a href="${im.link}" target="_blank" class="link">🔗 Ver</a></td></tr>`;
            });
            
            h+='</tbody></table></div></div>';
            div.innerHTML=h;
        }
        
        function limpar(){
            document.getElementById('imob').value='todas';
            document.getElementById('tipo').value='';
            ['pmin','pmax','amin','amax'].forEach(id=>document.getElementById(id).value='');
            document.getElementById('resultados').classList.remove('show');
        }
    </script>
</body>
</html>'''

@app.route('/buscar')
def buscar():
    imobiliaria = request.args.get('imob', 'todas')
    tipo = request.args.get('tipo', '')
    preco_min = float(request.args.get('pmin', 0))
    preco_max = float(request.args.get('pmax', 999999999))
    area_min = float(request.args.get('amin', 0))
    area_max = float(request.args.get('amax', 999999))
    
    imoveis = precificador.buscar_imoveis(
        imobiliaria,
        tipo if tipo else None,
        preco_min, preco_max,
        area_min, area_max
    )
    
    analise = precificador.analisar()
    
    return jsonify({'imoveis': imoveis, 'analise': analise})

if __name__ == '__main__':
    print("=" * 60)
    print("🏠 PRECIFICADOR - RECANTO DO VALE")
    print("=" * 60)
    print("\n🏢 Besser | Corretor e Cia | Sauthier")
    print("🌐 http://localhost:5000")
    print("=" * 60)
    
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)