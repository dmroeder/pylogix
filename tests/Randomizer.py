import random
import string


class Randomizer:
    '''
    Collectin of random values
    '''

    def Sint(self):
        '''
        Get a random 8 bit integer
        '''
        return random.randint(-128, 127)

    def Int(self):
        '''
        Get a random 16 bit integer
        '''
        return random.randint(-32768, 32767)

    def Dint(self):
        '''
        Get a random 32 bit integer
        '''
        return random.randint(-2147483648, 2147483647)

    def String(self):
        '''
         Get a random 8 bit integer
        '''
        integer = random.randint(1, 82)
        return ''.join(random.choice(string.ascii_letters) for i in range(integer))
