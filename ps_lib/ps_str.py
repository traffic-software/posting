import re
from sys import exit
import chardet
import itertools
import random
class ps_str:
	str = "ok now im ready for work with you and your software"
	def __init__(self,str):
		try:
			self.str = self.text_decode(str)
		except:
			self.str = str

		






	def text_decode(self,text):
		encodeinfo =chardet.detect(text)
		
		return text.decode(encodeinfo["encoding"])
	def get_text(self):
		return self.str

	def find_urls(self,condition):
		expression=r'(https?://\S+)'
		arg = re.findall(expression,self.str)
		url=None
		for d in arg:
			if condition in d:
				url = d
				break
		return url
	def find_email(self,expression):
		arg = re.search(expression,self.str)
		
		return arg.group() if arg else "nomail@mail.com"
	def options(self,s):
		# If the chunk is not empty or the chunk start with the split parameter
		# return the split by the variable | of the paramter
		if len(s) > 0 and s[0] == '{':
			return [opt for opt in s[1:-1].split('|')]
		return [s] # return empty in list to keep a list of lists

	
	
	def Spin(self):
		texts=[]
		
		chunk = re.split('(\{[^\}]+\}|[^\{\}]*)',self.str)

		# Return a list of lists of variations that can be combined
		opt_lists = [self.options(frag) for frag in chunk]

		for spec in itertools.product(*opt_lists):
			texts.append(''.join(spec))
		text=random.choice(texts)
		self.str = text
		return text
	def with_email(self,email):
		self.Spin()
		return self.str.replace("#email#", email)

