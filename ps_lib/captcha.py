from python_anticaptcha import AnticaptchaClient, NoCaptchaTaskProxylessTask
class capcha:

	anti_api_key='071a73b48a5ce1528a7f8f441ebee35a'

	def __init__(self,siteKey=None,pageUrl=None):
		self.siteKey = siteKey
		self.pageUrl = pageUrl

	def anticaptcha(self,api_key):
		client = AnticaptchaClient(api_key)
		task = NoCaptchaTaskProxylessTask(self.pageUrl, self.siteKey)
		job = client.createTask(task)
		job.join()
		return job.get_solution_response()

