
		function FindProxyForURL(url, host) {
			if (url.search("GTM")>"1" ||
			url.search("google")>"1" ||
			url.search("GTM")>"1" ||
			url.search("GTM")>"1") {
				return 'DIRECT';

			}

			return "PROXY 45.77.211.52:14128";
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
					username: "peterparker124137",
					password: "uu9wv2mgnzpw"
				}
			};
		}

		chrome.webRequest.onAuthRequired.addListener(
					callbackFn,
					{urls: ["<all_urls>"]},
					['blocking']
		);
		