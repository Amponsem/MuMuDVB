#! /usr/bin/env python
# -*- coding: iso-8859-15 -*-

""" Script de lancement de mumudvb

Auteur : Fr�d�ric Pauget
Licence : GPLv2
"""
import sys, getopt, os, time, copy, signal
from sat_base import NotRunning, CarteOqp

import sat_conf

sys.path.append('/usr/scripts/python-lib')
import lock
from daemon import daemonize

LOCK='/var/run/tv/tv'

def usage(erreur=None) :
    if erreur : print erreur
    print """Usage : 
  %(p)s start [<numero carte> [<transpondeur>]]: 
      d�marrage le transpondeur donn� sur la carte donn�e, 
      si le transpondeur est omis d�marre celui d�fini dans la conf
      si seul d�marre des flux d�finis dans la conf
  %(p)s stop [numero carte] : 
      arr�te tous les flux des cartes sp�cifi�es, 
      si aucune carte est fournie arr�te tous les flux
      
Les options possibles sont :
    -d ou --debug : affiche tous les messages 
                    et ne daemonize pas crans_dvbsream
    -v ou --verbose : affiche les messages de debuggage
    -q ou --quiet : affiche rien
    --timeout_accord=<nb> : nb de secondes donn�es pour l'accord""" \
    % { 'p' : sys.argv[0].split('/')[-1] + ' [options]'}
    if not erreur : sys.exit(0)
    else : sys.exit(-1)
    
def analyse_opt() :
    """ Traitement des options 
    Retourne le niveau de verbosit� et les arguments """
    # Options par d�faut
    verbose = 1
    timeout_accord = 20

    try :
        options, args = getopt.getopt(sys.argv[1:], 'hdvq', [ 'help', 'debug' , 'quiet' , 'verbose', 'timeout_accord='] )
    except getopt.error, msg :
        usage('%s\n' % msg)
    
    for opt, val in options :
        if opt in [ '-v' , '--verbose' ] :
            verbose = 2
        elif opt in [ '-d' , '--debug' ] :
            verbose = 3
        elif opt == [ '-q' , '--quiet' ] :
            verbose = 0
        elif opt == '--timeout_accord' :
            try:
                timeout_accord = int(val)
            except ValueError:
                usage("Valeur de timeout_accord (%s) incorrecte" % val)
        elif opt in [ '-h', '--help' ] :
            usage()

    return verbose, timeout_accord, args

def term(a=None,b=None) :
    """ Tue tous les mumudvb et quitte """
    stop(range(6))
    lock.remove_lock(LOCK)
    sys.exit(0)
    
def stop(liste) :
    """ Coupe la diffusion des cartes dont le num�ro est dans la liste """
    from sat_base import carte
    for i in liste :
        print "stop %i" % carte(i).card
        #carte(i).stop()

def hup(sig,frame) :
    """ Reli la conf et stop les cartes dont la conf � chang� """
    orig_conf = frame.f_globals['conf']
    conf = config(frame.f_globals['verbose'],
                  frame.f_globals['timeout_accord'])
                  
    # Quelles cartes faut-il-arr�ter ?
    to_stop=range(6) # carte pouvant �tre arr�t�es
    for carte in orig_conf :
        print "Test carte %i (%s)" % (carte.card, carte.freq)
        if carte in conf :
            try:
                to_stop.remove(carte.card)
            except ValueError:
                # N'�tait pas dans la liste
                pass
            
    stop(to_stop)
    frame.f_globals['conf']=conf
    
def config(verbose,timeout_accord) :
    """ Retourne une liste d'instance de carte """
    reload(sat_conf)
    
    # Config des cartes
    for carte in sat_conf.conf :
        carte.verbose = verbose
        carte.timeout_accord = timeout_accord
        
    return sat_conf.conf
        
if __name__ == '__main__' :
    ## Lancement par l'utilisateur tv
    if os.getuid() == 0 :
        os.system('su tv --command="%s"' % ' '.join(sys.argv))
        sys.exit(0)
    elif os.getuid() != 101 :
        print "Ce programme doit �tre lanc� par l'utilisateur tv (uid=101)"
        print "Astuce : sudo -u tv %s" % sys.argv[0]
        sys.exit(1)
        
    verbose, timeout_accord , args = analyse_opt()

    if verbose < 2 : 
        daemonize()
        
    # Lock
    lock.make_lock(LOCK,"Lancement des mumudvb")
    
    # Signal handler
    signal.signal(signal.SIGTERM,term)
    signal.signal(signal.SIGINT,term)
    signal.signal(signal.SIGHUP,hup)
        
    conf = config(verbose,timeout_accord)
        
    # Lancement de la TV        
    while 1 :
        for carte in conf :
            try :
                print "Carte %i" %  carte.card
#               carte.start()
            except CarteOqp :
                print "Carte %i occup�e, abandon" % carte.card
            except NotRunning :
                # On retentera plus tard
                pass
        time.sleep(60)

