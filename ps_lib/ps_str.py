import re
import chardet
class ps_str:
	str = "oknow im ready for work with you and your software"
	def __init__(self,str):
		self.str = self.text_decode(str)






	def text_decode(self,text):
		encodeinfo =chardet.detect(text)
		print(encodeinfo["encoding"])
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
