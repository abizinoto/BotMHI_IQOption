from iqoptionapi.stable_api import IQ_Option
import configparser, time
from datetime import datetime, timedelta

"""
16:40:00 0.00 1.12364 1.12362 
16:41:00 1.00 1.123625 1.12359
16:42:00 2.00 1.123575 1.12361      - Candle 1 de configuração
16:43:00 3.00 1.123615 1.12361      - Candle 2 de configuração
16:44:00 4.00 1.123605 1.12361      - Candle 3 de configuração
16:45:00 5.00 1.123615 1.12361      - IN
16:46:00 6.00 1.12362 1.123675      - G1
16:47:00 7.00 1.123675 1.12366      - G2                            - Candle 1 de configuração
16:48:00 8.00 1.12365 1.123665                                      - Candle 2 de configuração
16:49:00 9.00 1.123665 1.12362                                      - Candle 3 de configuração
16:50:00 0.00 1.123625 1.123585                                     - IN
16:51:00 1.00 1.12358 1.123465                                      - G1
16:52:00 2.00 1.12345 1.123375                                      - G2                            - Candle 1 de configuração

"""
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
    
conf = configuracao()
API = IQ_Option(conf['email'],conf['senha'])
API.connect()
API.change_balance('PRACTICE') # PRACTICE / REAL
if API.check_connect():
        print(' Conectado com sucesso - Operadora : IQ OPtion!')
else:
    print(' Erro ao conectar')
    input('\n\n Aperte enter para sair')
    exit()

def analisa_par_mhi(par, tf = 1, tempo = 2, payout=87):
    tempo = 2 * 60  # (2 horas)
    tf = 1 * 60     # (1 minuto)
    velas = API.get_candles(par, tf, tempo, time.time())

    vela_ciclo = [0,0,0,0,0,0,0,0,0,0]     # Matriz de ciclo
    operacao = ['','','','','']
    analises = []


    ct_ent = 0
    ct_g1 = 0
    ct_g2 = 0
    ct_loss = 0 
    dir = ''

    for vela in velas:
        min_calc = datetime.fromtimestamp(vela['from']).strftime('%M.%S')[1:2]
        hora = datetime.fromtimestamp(vela['from']).strftime('%H:%M:%S')

        vela_ciclo[int(min_calc)] = 'g' if vela['open'] < vela['close'] else 'r' if vela['open'] > vela['close'] else 'd'

        if min_calc == '2': 
            #vela_ciclo[7:10].count() = determinam a operacao
            if vela_ciclo[7:10].count('g') > vela_ciclo[7:10].count('r') and vela_ciclo[7:10].count('d') == 0 : dir = 'put'
            if vela_ciclo[7:10].count('r') > vela_ciclo[7:10].count('g') and vela_ciclo[7:10].count('d') == 0 : dir = 'call'
            gain_ent = (dir == 'put' and vela_ciclo[0] == 'r') or (dir == 'call' and vela_ciclo[0] == 'g')  #IN
            gain_g1 = (dir == 'put' and vela_ciclo[1] == 'r') or (dir == 'call' and vela_ciclo[1] == 'g') # g2
            gain_g2 = (dir == 'put' and vela_ciclo[2] == 'r') or (dir == 'call' and vela_ciclo[2] == 'g') # g1

            if gain_ent:
                res = 'IN'
                ct_ent += 1
            elif gain_g1:
                res = 'G1'
                ct_g1 += 1
            elif gain_g2:
                res = 'G2'
                ct_g2 += 1
            else:
                res = 'LOSS'
                ct_loss += 1
                
            if dir != '':
                operacao= [par, hora, dir, res]
                analises.append(operacao)
            
        if min_calc == '7':
            #vela_ciclo[2:5].count() = determinam a operacao
            if vela_ciclo[2:5].count('g') > vela_ciclo[2:5].count('r') and vela_ciclo[2:5].count('d') == 0 : dir = 'put'
            if vela_ciclo[2:5].count('r') > vela_ciclo[2:5].count('g') and vela_ciclo[2:5].count('d') == 0 : dir = 'call'
            gain_ent = (dir == 'put' and vela_ciclo[5] == 'r') or (dir == 'call' and vela_ciclo[5] == 'g')  #IN
            gain_g1 = (dir == 'put' and vela_ciclo[6] == 'r') or (dir == 'call' and vela_ciclo[6] == 'g') # g2
            gain_g2 = (dir == 'put' and vela_ciclo[7] == 'r') or (dir == 'call' and vela_ciclo[7] == 'g') # g1
            
            if gain_ent:
                res = 'IN'
                ct_ent += 1
            elif gain_g1:
                res = 'G1'
                ct_g1 += 1
            elif gain_g2:
                res = 'G2'
                ct_g2 += 1
            else:
                res = 'LOSS'
                ct_loss += 1
                
            if dir != '':
                operacao = [par, hora, dir, res]
                analises.append(operacao)
    
    ct_win = ct_ent + ct_g1 + ct_g2
    ct_operacoes = ct_ent + ct_g1 + ct_g2 + ct_loss
    estat = { 
            'qt_operacoes' : ct_operacoes,
            'qt_entradas' : ct_ent,
            'qt_g1' : ct_g1,
            'qt_g2' : ct_g2,
            'qt_loss_se_g2' : ct_loss,
            'tx_gain_g2': ((ct_ent + ct_g1 + ct_g2) / (ct_operacoes * 100)),
            'qt_loss_se_g1' : (ct_g2 + ct_loss),
            'qt_loss_sem_gale' : (ct_g1 + ct_g2 + ct_loss),
            'tx_gain_real_ent' : ((ct_ent) * payout/100 - ((ct_g1 + ct_g2 + ct_loss))),
            'tx_gain_real_g1' : ((ct_ent + ct_g1) * payout/100 - ((ct_g2 + ct_loss)* 3)),
            'tx_gain_real_g2' : (ct_win * payout/100 - (ct_loss * 7) )}


    return estat

analisa_par_mhi('EURJPY', 1, 2, 87)

"""    
    for linha in analises:
        print(linha)print('\nQuantidade de Operações      : ',ct_operacoes)
    print('Quantidade de Ent            : ',ct_ent)
    print('Quantidade de G1             : ',ct_g1)
    print('Quantidade de G2             : ',ct_g2)
    print('Quantidade de LOSS até G2    : ',ct_loss)
    print('Total de WIN:                : ',ct_win)
    
    print('Taxa de GAIN até G2          : {:.2f}%'.format((ct_ent + ct_g1 + ct_g2) / ct_operacoes * 100))
    print('Ganho real até g2 (payout médio 87%): {:.2f}%'.format(ct_win * payout/100- (ct_loss * 7) ))
    
    print('\nQuantidade de LOSS até G1    : ', (ct_g2 + ct_loss))
    print('Ganho real até g1(payout médio 87%): {:.2f}%'.format(((ct_ent + ct_g1) * payout/100 - (ct_g2 + ct_loss) )))

    print('\nQuantidade de LOSS sem Gale    : ', (ct_g1 + ct_g2 + ct_loss))
    print('Ganho real até g1(payout médio 87%): {:.2f}%'.format(((ct_ent) * payout/100 - (ct_g1 + ct_g2 + ct_loss) )))
"""
