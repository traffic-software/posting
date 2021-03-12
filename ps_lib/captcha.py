from python_anticaptcha import AnticaptchaClient, NoCaptchaTaskProxylessTask
class capcha:

	anti_api='071a73b48a5ce1528a7f8f441ebee35a'

	def __init__(self,anti_api_key=None):
		self.anti_api = anti_api_key
		print(self.anti_api)

	def anticaptcha(self,siteKe,pageUrl):
		client = AnticaptchaClient(self.anti_api)
		task = NoCaptchaTaskProxylessTask(pageUrl, siteKe)
		job = client.createTask(task)
		job.join()
		print('task done')
		return job.get_solution_response()

