
		function FindProxyForURL(url, host) {
			if (url.search("GTM")>"1" ||
			url.search("google")>"1" ||
			url.search(".js")>"1" ||
			url.search(".png")>"1" ||
			url.search(".jpg")>"1" ||
			url.search(".jpeg")>"1" ||
			url.search(".css")>"1") {
				return 'DIRECT';

			}

			return "PROXY proxy.soax.com:9270";
			}
		var config = {
		mode: "pac_script",
		pacScript: {
			data:FindProxyForURL.toString(),
    		mandatory: true
			}
		};

		chrome.proxy.settings.set({value: config, scope: "regular"}, function() {});

		function callbackFn(details) {
			return {
				authCredentials: {
					username: "8r047OnpQlHArmEZ",
					password: "wifi;us;;;milwaukee;"
				}
			};
		}

		chrome.webRequest.onAuthRequired.addListener(
					callbackFn,
					{urls: ["<all_urls>"]},
					['blocking']
		);
		