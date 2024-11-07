from .DFA import DFA

from dataclasses import dataclass
from collections.abc import Callable
from collections import deque
EPSILON = ''  # this is how epsilon is represented by the checker in the transition function of NFAs


@dataclass
class NFA[STATE]:
    S: set[str]
    K: set[STATE]
    q0: STATE
    d: dict[tuple[STATE, str], set[STATE]]
    F: set[STATE]

    def epsilon_closure(self, state: STATE) -> set[STATE]:
        # compute the epsilon closure of a state (you will need this for subset construction)
        # see the EPSILON definition at the top of this file
        res={state} # setu-ul in care pun toate starile la care se poate ajunge prin epsilon-tranzitii
        stari_de_vizitat=[] # lista in care retin starile ce terbuie explorate
        stari_de_vizitat.append(state)
        while stari_de_vizitat:
            stare_cur=stari_de_vizitat.pop()
            if (stare_cur,EPSILON) in self.d:
                # daca exista tranzitie pe epsilon din starea curenta
                # trebuie sa explorez toti vecinii catre care se poate ajunge
                vecini=self.d[(stare_cur,EPSILON)]
                for vecin in vecini:
                    # astfel adaug toti vecinii nevizitati deja in lsiat de stari ce trebuie explorate
                    if vecin not in res:
                        res.add(vecin)
                        stari_de_vizitat.append(vecin)
        return res

    def subset_construction(self) -> DFA[frozenset[STATE]]:
        # convert this nfa to a dfa using the subset construction algorithm
        # incep din prima stare care este reprezentata de starea initiala + 
        # inchiderea epsilon a acesteia 
        stare_initial = stare_initial = frozenset(self.epsilon_closure(self.q0))
        # o adaug intr-o coada intrucat vom ajunge sa avem mai multe stari 
        # pe care va trebui sa le vizitam
        coada = deque([stare_initial]) 
        # initializez datele in care retin starile DFA-ului construit
        d2 = {}
        F2 = set()
        K2 = {stare_initial}
        ssink = frozenset({'sink'})
        ok=0  
        while coada:
            # scot o stare din coada
            aux = coada.popleft()
            # verific daca in setul de stari grupate exista macar o stare care sa fie 
            # stare final in NFA. Daca exista adaug si setul cu totul in setul de stari finale al DFA-ului
            for s in aux:
                if s in self.F:
                    F2.add(aux)
            for c in self.S:
                # pentru fiecare caracter din alfabet trebuie sa aflu 
                # care este tarnzitia din setul curent de stari
                stare_noua = set()
                for x in aux:
                    # verific tranzitiile fiecarei stari din set pe caracterul curent
                    if (x, c) in self.d:
                        for ss in self.d[(x, c)]:
                            # daca exista tranzitia din starea respectiva actualizez set-ul urmator de stari cu
                            # starea urmatoare + inchiderea epsilon a acesteia
                            stare_noua.update(self.epsilon_closure(ss))
                if stare_noua:
                    # ajung daca exista tranzitie pe caracterul c din setul curent de stari
                    d2[(aux, c)] = frozenset(stare_noua) # adaug tranzitia in dictionarul de tranziiti al dfa-ului
                    if frozenset(stare_noua) not in K2:
                        # daca setul de stari nou descoperit nu mai exista deja 
                        # il adaug in setul de stari al dfa-ului
                        K2.add(frozenset(stare_noua))
                        # il adaug si in coada pentru a fi explorat si el
                        coada.append(frozenset(stare_noua)) 
                else:
                    # aici inseamna ca nu exista tranzitie pe c din setul curent de stari
                    # asadar fac ca tranzitie pe c din setul curent catre 'sink state'
                    d2[(aux, c)] = ssink
                    ok = 1 # marchez ca am nevoie de sink state in DFA

        if ok==1:
            # inseamna ca am nevoie de sink state
            K2.add(ssink) # adaug sink state la stari
            for symbol in self.S:
                # fac ca din sink state pe orice caracter din alfabet 
                # sa se faca tranzitie tot in sink state
                d2[(ssink, symbol)] = ssink

        return DFA(S=self.S, K=K2, q0=stare_initial, d=d2, F=F2)


    def remap_states[OTHER_STATE](self, f: 'Callable[[STATE], OTHER_STATE]') -> 'NFA[OTHER_STATE]':
        # optional, but may be useful for the second stage of the project. Works similarly to 'remap_states'
        # from the DFA class. See the comments there for more details.
        pass
