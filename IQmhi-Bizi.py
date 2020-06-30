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
'''

from iqoptionapi.stable_api import IQ_Option
from datetime import datetime
import time
import sys
import configparser


def stop(lucro, gain, loss):
	if lucro <= float('-' + str(abs(loss))):
		print('Stop Loss batido!')
		sys.exit()
		
	if lucro >= float(abs(gain)):
		print('Stop Gain Batido!')
		sys.exit()

def Martingale(valor, payout):
	lucro_esperado = valor * payout
	perda = float(valor)	
		
	while True:
		if round(valor * payout, 2) > round(abs(perda) + lucro_esperado, 2):
			return round(valor, 2)
			break
		valor += 0.01

def Payout(par, tipo = 'turbo'):
	if tipo == 'turbo':		
		a = API.get_all_profit()
		return  int(100 * a[par]['turbo'])
	else:
		API.subscribe_strike_list(par,1)
		while True:
			d = API.get_digital_current_profit(par, 1)
			if d != False:
				d = round(int(d) / 100, 2)
				break
			time.sleep(1)
		API.unsubscribe_strike_list(par, 1)
		return d

print('''
 -----------------------------------------------------
     BOT-Estratégia - MHI - IQOptions - \x1b[0;37;42m@abizinoto\x1b[0m
 -----------------------------------------------------
''')

def configuracao():
    
    arquivo = configparser.RawConfigParser()
    arquivo.read('config.txt')
    
    return {'email': arquivo.get('GERAL', 'email'), 'senha': arquivo.get('GERAL', 'senha'), 'valor': arquivo.get('GERAL', 'valor'), 'opcao': arquivo.get('GERAL', 'opcao'), 'limite_payout': arquivo.get('GERAL', 'limite_payout'), 'valor': arquivo.get('GERAL', 'valor')}


conf = configuracao()
API = IQ_Option(conf['email'],conf['senha'])


API.connect()

API.change_balance('PRACTICE') # PRACTICE / REAL

if API.check_connect():
	print(' Conectado com sucesso - Operadora : IQ OPtion!')
else:
	print(' Erro ao conectar')
	input('\n\n Aperte enter para sair')
	sys.exit()

par = input(' Indique uma paridade para operar: ').upper()
valor_entrada = float(input(' Indique um valor para entrar: '))
valor_entrada_b = float(valor_entrada)


martingale = int(input(' Indique a quantia de martingales (max 3): '))
martingale += 1

stop_loss = float(input(' Indique o valor de Stop Loss: '))
stop_gain = float(input(' Indique o valor de Stop Gain: '))
min_payout = float(input(' Indique o Payout minimo para a operação: ')) / 100

# TESTE
"""par = 'GBPJPY'
valor_entrada = 10.0
martingale = 2
stop_loss = 100.0
stop_gain = 100.0
min_payout = 0.79"""
opcoes = (input(' Indique o tipo de Opções (<B>inárias ou <D>igital: ')).upper()

confirma = ''
while True:
	confirma = input('\n Favor conferir os dados acima e digite [Sim] para prosseguir: ')
	if confirma == "Sim":
		break

opcao_escolhida = 'digital' if opcoes == 'D' else 'turbo'

lucro = 0
payout = Payout(par, opcao_escolhida)
ant_payout = 0

print('\n Bot iniciado... no par: {} opçoes {} em: {}\n'.format(par, 'Binárias' if opcoes == 'B' else 'Digitais', (datetime.now()).strftime("%d-%m-%Y %H:%M:%S")))
while True:
	minutos = float(((datetime.now()).strftime('%M.%S'))[1:])

	if (minutos >= 3.00 and minutos <= 3.5) or (minutos >= 7 and minutos <= 7.5):
		payout = Payout(par, opcao_escolhida)		
		if payout < min_payout and payout != ant_payout:
			print(f'Aguardando - Payout {payout * 100}% abaixo do mínimo {min_payout * 100}% !!!')
			ant_payout = payout

	entrar = True if ((minutos >= 4.58 and minutos <= 5) or minutos >= 9.58) and payout >= min_payout else False

	#print('Hora de entrar?',entrar,'/ Minutos:',minutos)
	
	if entrar:
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
						while True:
							status,valor = API.check_win_digital_v2(id)
							
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
						while True:
							status,valor = API.check_win_v2(id)
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
						print(' ERRO AO REALIZAR OPERAÇÃO PAR {par} OPÇÃO {opcao_escolhida}!!')

	time.sleep(0.5)
print('\n Bot finalizado as {}\n'.format((datetime.now()).strftime("%Y-%m-%d %H:%M:%S")))
