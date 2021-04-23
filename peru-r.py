from requests_html import HTMLSession
session = HTMLSession()
r = session.get('https://pe.skokka.com/u/post-insert/')
r.html.render()
data = r.html.find('.skokka', first=True)
print(data.html)
