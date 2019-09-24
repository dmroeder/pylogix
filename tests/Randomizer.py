'''
   Originally created by Burt Peterson
   Updated and maintained by Dustin Roeder (dmroeder@gmail.com) 

   Copyright 2019 Dustin Roeder

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
'''

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
