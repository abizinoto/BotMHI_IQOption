'''
	BOT MHI v1.1
	- Analise em 1 minuto
	- Entradas para 1 minuto
	- Calcular as cores das velas de cada quadrado, ultimas 3 velas, minutos: 2, 3 e 4 / 7, 8 e 9
	- Entrar contra a maioria
	
	- Estrategia retirada do video https://www.youtube.com/watch?v=FePy1GY2wqQ	

	DEV-BACKLOG - Bizi
	- Melhorar tempo do gale
	- implementar filtro de Payout - OK
	- Incluir opçao de binárias - OK
	- exportar Listagem de operações para planilha
	- Incluir avisos e opção de não operar em notícias  - OK 
		https://botpro.com.br/calendario-economico/
	- Calcular entrada/gale de fechamento somente para meta ou para loss 
'''

from iqoptionapi.stable_api import IQ_Option
from datetime import datetime, timedelta
from estrategia import analisa_par_mhi

import time
import sys
import configparser
import requests
import json
import urllib3

def stop(lucro, gain, loss):
	if lucro <= float('-' + str(abs(loss))):
		print('Stop Loss batido!')
		sendtelegram('Stop Loss Batido! Loss de {}. Bot finalizado.'.format(str(abs(loss))))
		sys.exit()
		
	if lucro >= float(abs(gain)):
		print('Stop Gain Batido!')
		sendtelegram('Stop Gain Batido! Gain de {}. Bot finalizado.'.format(str(lucro)))
		sys.exit()

def Martingale(valor, payout):
	lucro_esperado = valor * payout
	perda = float(valor)	
		
	while True:
		if round(valor * payout, 2) > round(abs(perda) + lucro_esperado, 2):
			return round(valor, 2)
			break
		valor += 0.01
        
def Payout(par, tipo = 'turbo', payout_ant = 70):
	if tipo == 'turbo':		
		a = API.get_all_profit()
		return  int(a[par]['turbo'])   #payout em formato de taxa: exemplo 0.78
	else:
		timeout_digital = 4
		API.subscribe_strike_list(par,1)
		for x in range(timeout_digital):
			d = API.get_digital_current_profit(par, 1)
			if d != False:
				d = round(int(d) / 100, 2)
				break
			x += 1
			time.sleep(1)
		API.unsubscribe_strike_list(par, 1)
		return d

def configuracao():
    
    arquivo = configparser.RawConfigParser()
    arquivo.read('config.txt')
    
    return {'email': arquivo.get('GERAL', 'email'), 
            'senha': arquivo.get('GERAL', 'senha'), 
            'valor': arquivo.get('GERAL', 'valor'), 
            'opcao': arquivo.get('GERAL', 'opcao'), 
            'limite_payout': arquivo.get('GERAL', 'limite_payout'),
            'TELEGRAM_TOKEN': arquivo.get('GERAL','TelegramToken'),
            'TELEGRAM_CHATID': arquivo.get('GERAL','TelegramChatId')}

def sendtelegram(message):
	global conf
	send_text = 'https://api.telegram.org/bot' + conf['TELEGRAM_TOKEN'] + '/sendMessage?chat_id=' + conf['TELEGRAM_CHATID'] + '&parse_mode=Markdown&text=' + message
	return requests.get(send_text)

def payout(par, tipo, check = True, timeframe = 1):
    if check:
        pares = API.get_all_open_time()
        if tipo == 'turbo' and pares['turbo'][par]['open']==True:
            a = API.get_all_profit()
            return  int(100 * a[par]['turbo'])
        elif tipo == 'digital' and pares['digital'][par]['open']==True:
            API.subscribe_strike_list(par, timeframe)
            while True:
                d = API.get_digital_current_profit(par, timeframe)
                if d != False:
                    d = int(d)
                    break
                time.sleep(1)
            API.unsubscribe_strike_list(par, timeframe)
            return d
        else:
            return 0
    else:
        if tipo == 'turbo':
            a = API.get_all_profit()
            return  int(100 * a[par]['turbo'])
        elif tipo == 'digital':
            API.subscribe_strike_list(par, timeframe)
            while True:
                d = API.get_digital_current_profit(par, timeframe)
                if d != False:
                    d = int(d)
                    break
                time.sleep(1)
            API.unsubscribe_strike_list(par, timeframe)
            return d
        else:
            return 0
        
def best_bet(par, check = True):
    binaria = payout(par,'turbo', check,5)
    digital = payout(par,'digital',check,5)
    if binaria >= digital:
        return 'turbo', binaria
    elif digital > binaria:
        return 'digital', digital
    else:
        return 'closed',0

def show_stats():
	print('\n Estatística dos Pares abertos (ultimas 2h):')
	print(' -------------------------------------------------------------------------------------')
	busca_pares = API.get_all_open_time()
	for par in busca_pares['turbo']:
		if busca_pares['turbo'][par]['open'] == True:
			tipo, payout = best_bet(par, True)
			stat = analisa_par_mhi(par, 1, 2, payout)
			print(' {} -> Melhor payout: {:8} {} | Taxa de ganho IN: {: 6.2f}, G1 {: 6.2f}, G2 {: 6.2f}'.format(par, tipo, payout, (stat['tx_gain_real_ent']), stat['tx_gain_real_g1'],stat['tx_gain_real_g2']))

	for par in busca_pares['digital']:
		if busca_pares['digital'][par]['open'] == True: # and par not in pares and par != "GBPJPY-OTC":
			tipo, payout = best_bet(par, True)
			stat = analisa_par_mhi(par, 1, 2, payout)
			print(' {} -> Melhor payout: {:8} {} | Taxa de ganho IN: {: 6.2f}, G1 {: 6.2f}, G2 {: 6.2f}'.format(par, tipo, payout, (stat['tx_gain_real_ent']), stat['tx_gain_real_g1'],stat['tx_gain_real_g2']))
	print(' -------------------------------------------------------------------------------------')

def noticias(par, tempo=15, detalhar = False):      # noticias.check(par, 30)
	global dados
	possui_noticias = False
	for key in dados['result']:
		hora_noticia = datetime.strptime(str(key['data']),"%Y-%m-%d %H:%M:%S")  # time.strptime((str(key['data']),"%d %b %y %H:%M:%S"))
		hora_atual = datetime.now() #).strftime("%Y-%m-%d %H:%M:%S")
		hora_noticia_s = time.mktime(hora_noticia.timetuple())
		hora_atual_s = time.mktime(hora_atual.timetuple())
		minutos_diferenca = int(hora_noticia_s-hora_atual_s) / 60
		if (par.count(key['economy']) > 0) and (key['impact']> 1) and (minutos_diferenca > -tempo and minutos_diferenca < tempo):
			possui_noticias = True
			if detalhar:
				print(' Noticias de {} {} touros as {} >>> {}'.format(key['economy'], key['impact'], key['data'][11:17], key['name']))
	return possui_noticias

def check_cor_vela_win(par, tempo, dir, lucro):
    
	tempo = tempo * 60
	while True:
		minutos5 = float(((datetime.now()).strftime('%M.%S'))[1:])
		minutos1 = float(((datetime.now()).strftime('%S')))
		minutos = minutos1 if tempo == 60 else minutos5
		if (minutos >= 4.58 and tempo == 5*50) or (minutos > 58.0 and tempo == 1*60):
			vela = API.get_candles(par, tempo, 1, time.time())
			dir_vela = 'call' if vela[0]['open'] < vela[0]['close'] else 'put' if vela[0]['open'] > vela[0]['close'] else 'doji'
			break
	return True, (lucro) if dir == dir_vela else 0

#====================================================================================#
# =============================   INICIO DO ROBO   ================================= #
#====================================================================================#

print('''
 -----------------------------------------------------
     BOT-Estratégia - MHI - IQOptions - abizinoto
 -----------------------------------------------------''')

conf = configuracao()
API = IQ_Option(conf['email'],conf['senha'])
API.connect()
print(' API : {} \n'.format(API.__version__))
      
if API.check_connect():
	print(' Conectado com sucesso - Operadora : IQ OPtion!')
else:
	print(' Erro ao conectar')
	input('\n\n Aperte enter para sair')
	sys.exit()
 
API.change_balance('PRACTICE') # PRACTICE / REAL
 
input_default = False	# Default=False >>> Trocar para True para efetuar testes e não precisar entrar com os dados de parametros

if (input(' Deseja processar a estatística dos pares (S/N)? :')).upper()[:1] == 'S':
	show_stats()

if not input_default:
	par = input(' Indique uma paridade para operar: ').upper()
	valor_entrada = float(input(' Indique um valor para entrar: '))
	valor_entrada_b = float(valor_entrada)

	martingale = int(input(' Indique a quantia de martingales (max 3): '))
	martingale += 1

	stop_loss = float(input(' Indique o valor de Stop Loss: '))
	stop_gain = float(input(' Indique o valor de Stop Gain: '))
	min_payout = float(input(' Indique o Payout minimo para a operação: ')) / 100
	cons_noticias = (input(' Considerar não operar com notícias acima de 1 touro? (S/N): ' )).upper()
	if cons_noticias == 'S':
		num_min_noticias = int(input(' Quandos minutos desconsiderar para as notícias: '))
	else:
		num_min_noticias = 0

	opcoes = (input(' Indique o tipo de Opções (<B>inárias ou <D>igital: ')).upper()

	confirma = ''
	while True:
		confirma = input('\n Favor conferir os dados acima e digite [Sim] para prosseguir: ')
		if confirma == "Sim":
			break
else:		# Entradas de Teste
	par = 'EURUSD' # 'GBPJPY'
	valor_entrada = 30.0
	martingale = 2
	stop_loss = 100.0
	stop_gain = 150
	min_payout = 0.60
	opcoes = 'D'
	valor_entrada_b = float(valor_entrada)
	cons_noticias = 'S'
	num_min_noticias = 15

opcao_escolhida = 'digital' if opcoes == 'D' else 'turbo'

# noticias.init()   Busca dados do Investing.com  // testar notícias
http = urllib3.PoolManager()
jsonurl = 'https://botpro.com.br/calendario-economico/'
r = http.request('GET', jsonurl)
dados = json.loads(r.data)
#noticias = dados['result']

lucro = 0
payout = Payout(par, opcao_escolhida)
ant_payout = 0

telegram_erro = sendtelegram('Bizi IMH Bot iniciado no par {} opçoes {} por {}'.format(par, 'Binarias' if opcoes == 'B' else 'Digitais', conf['email']))
      
print('\n Bot iniciado... no par: {} opçoes {} em: {}\n'.format(par, 'Binárias' if opcoes == 'B' else 'Digitais', (datetime.now()).strftime("%d-%m-%Y %H:%M:%S")))
if cons_noticias == 'S' and noticias(par, num_min_noticias, True):
    
    print(' Robo não irá operar entre: {} e {} devido as noticias abaixo:'
          .format((datetime.now() - timedelta(minutes=num_min_noticias)).strftime('%H:%M'), 
                  (datetime.now() + timedelta(minutes=num_min_noticias)).strftime('%H:%M')))
    noticias(par, num_min_noticias, True)

while True:
	minutos = float(((datetime.now()).strftime('%M.%S'))[1:])

	if (minutos >= 3.00 and minutos <= 3.5) or (minutos >= 7 and minutos <= 7.5):
		payout = Payout(par, opcao_escolhida, payout)		
		if payout < min_payout and payout != ant_payout:
			print(f'Aguardando - Payout {payout * 100}% abaixo do mínimo {min_payout * 100}% !!!')
			ant_payout = payout

	entrar = True if ((minutos >= 4.58 and minutos <= 5) or minutos >= 9.58) and payout >= min_payout else False

	#print('Hora de entrar?',entrar,'/ Minutos:',minutos)
	
	if entrar and (cons_noticias == 'S' and not noticias(par, num_min_noticias)):
		
		#print('Iniciando operação!', end=":")
		dir = False
		print('\n Par {} : Min {} - Velas:'.format(par, (datetime.now()).strftime('%H:%M:%S')), end='')
		velas = API.get_candles(par, 60, 3, time.time())
		
		velas[0] = 'g' if velas[0]['open'] < velas[0]['close'] else 'r' if velas[0]['open'] > velas[0]['close'] else 'd'
		velas[1] = 'g' if velas[1]['open'] < velas[1]['close'] else 'r' if velas[1]['open'] > velas[1]['close'] else 'd'
		velas[2] = 'g' if velas[2]['open'] < velas[2]['close'] else 'r' if velas[2]['open'] > velas[2]['close'] else 'd'

		cores = velas[0] + ' ' + velas[1] + ' ' + velas[2]	

		if cores.count('g') > cores.count('r') and cores.count('d') == 0 : dir = 'put'
		if cores.count('r') > cores.count('g') and cores.count('d') == 0 : dir = 'call'	
		
		cores = cores.replace('r','\x1b[0;37;41mR\x1b[0m')
		cores = cores.replace('g','\x1b[0;37;42mG\x1b[0m')
		cores = cores.replace('d','\x1b[5;37;47mD\x1b[0m')	
		print(cores, end = " | ")
		
		if dir:
			print('Direção:',dir.upper())
			valor_entrada = valor_entrada_b
			for i in range(martingale):
				if opcoes == 'D':
					status,id = (API.buy_digital_spot(par, valor_entrada, dir, 1))
					if status:
						time.sleep(10)

						while True:
							#status,valor = API.check_win_digital_v4(id)
							status, valor = check_cor_vela_win(par, 1, dir, valor_entrada * payout)
							
							if status:
								valor = valor if valor > 0 else float('-' + str(abs(valor_entrada)))
								lucro += round(valor, 2)
								
								print(' --> Resultado operação: ', end='')
								print('WIN /' if valor > 0 else 'LOSS /' , round(valor, 2) ,'/', round(lucro, 2),('/ '+str(i)+ ' GALE' if i > 0 else '' ))
								
								valor_entrada = Martingale(valor_entrada, payout)
								
								stop(lucro, stop_gain, stop_loss)
								
								break
								
						if valor > 0 : break
					else:
						print(f' ERRO AO REALIZAR OPERAÇÃO PAR {par} OPÇÃO {opcao_escolhida}!')
				else:
					status, id = (API.buy(valor_entrada, par, dir, 1))
					if status:
						time.sleep(10)
						while True:
							#status,valor = API.check_win_v3(id)
							status, valor = check_cor_vela_win(par, 1, dir, valor_entrada * payout)
							if status:
								valor = valor if valor > 0 else float('-' + str(abs(valor_entrada)))
								lucro += round(valor, 2)
								
								print(' --> Resultado operação: ', end='')
								print('WIN /' if valor > 0 else 'LOSS /' , round(valor, 2) ,'/', round(lucro, 2),('/ '+str(i)+ ' GALE' if i > 0 else '' ))
								
								valor_entrada = Martingale(valor_entrada, payout)
								
								stop(lucro, stop_gain, stop_loss)
								
								break
								
							if valor > 0 : break
						else:
							print(f'\n ERRO AO REALIZAR OPERAÇÃO PAR {par} OPÇÃO {opcao_escolhida}!!')
	elif entrar and cons_noticias == 'S' and noticias(par, num_min_noticias, True):
		print(' Robo não irá operar entre: {} e {} devido as noticias abaixo:'
              .format((datetime.now() - timedelta(minutes=num_min_noticias)).strftime('%H:%M'), 
                      (datetime.now() + timedelta(minutes=num_min_noticias)).strftime('%H:%M')))
		noticias(par, num_min_noticias, True)
	time.sleep(0.5)
sendtelegram('\n Bot finalizado')
print('\n Bot finalizado as {}\n'.format((datetime.now()).strftime("%Y-%m-%d %H:%M:%S")))
