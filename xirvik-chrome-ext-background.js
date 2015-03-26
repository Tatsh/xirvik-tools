            var options;

            var options_default = {

                servers:   [],
                click:     false,       /* Capture torrent clicks */
                capture:   0,           /* Capture mode */
                messageds: false,       /* Download start + */
                messagedf: true,        /* Download failure */
                messageus: false,       /* Upload start + */
                messageuc: true,        /* Upload success + */
                messageuf: true,        /* Upload failure */
                messagesf: true,        /* Server login failure */
                messagest: true,        /* Server connection timeout */
                nostart:   false,       /* Upload without starting the torrent automatically */
                labels:    false,       /* Edit labels before uploading each torrent */
                dirs:      false,       /* Edit directories before uploading each torrent */
                timeout:   15,          /* Timeout value, in seconds, for server connections */
                console:   false,       /* Show console output */
                promos:    true,        /* keep track of promo messages? */
                promostamp:"",          /* UNIX timestamp of the last promo received */
            };

            function load()
            {
                console.log("[Xirvik] Starting up.");

                options = JSON.parse(getItem("options"));

                if(!options)
                {
                    options = options_default;
                }

                if(typeof(options.promos) == "undefined")
                {
                    options.promos = true;
                }

                if(options.console)
                    console.log("[Xirvik] Options loaded - console output is on.");

                checkPromo();
                setInterval(checkPromo, 1000 * 60 * 60);
            }

			function setItem(key, value)
			{
				try
				{
					window.localStorage.removeItem(key);
					window.localStorage.setItem(key, value);
				}
				catch(e) { }
			}

			function getItem(key)
			{
				var value;

				try
				{
					value = window.localStorage.getItem(key);
				}
				catch(e)
				{
					value = "null";
				}

				return value;
			}

            function showNotification(theme, text)
            {
                if(options.console)
                    console.log("[Xirvik] Creating notification: \"" + text + "\"");

                var notification = webkitNotifications.createNotification('xirvik-48.png', theme, text);

                notification.show();

                setTimeout(function()
                {
                    notification.cancel();
                },
                5000);
            }

            /* */
 
            function checkPromo()
            {
                if(options.promos)
                {
                    var timestamp = options.promostamp;

                    if(!timestamp || !timestamp.length)
                        timestamp = new Date().getTime();
                        
                    // 00 => User doesn't have any configured seedbox
                    // 01 => None of the configured seedboxes are xirvik's (ie none of the URLs are in the xirvik.com domain)
                    // 02 => All of the configured seedboxes are xirvik's
                    // 03 => User has both xirvik and non-xirvik seedboxes
                    var type = "00", hasX = false, hasOther = false;

                    for(var j = 0; j < options.servers.length; j++)
                    {
                        var uri = options.servers[j].host;

                        if(uri.indexOf("xirvik.com") != -1)
                        {
                            hasX = true;
                        }
                        else
                        {
                            hasOther = true;
                        }
                    }

                    if(hasX && hasOther)
                    {
                        type = "03";
                    }
                    else
                    {
                        if(hasX)
                        {
                            type = "02";
                        }
                        else if(hasOther)
                        {
                            type = "01";
                        }
                    }

                    var xhr = new XMLHttpRequest(), xhrtimer = null;
                    xhr.open('GET', "http://localhost/xirvik/promo_news.php?timestamp=" + timestamp + "&type=" + type);

                    xhr.onreadystatechange = function(res)
                    {
                        if(xhr.readyState == 4)
                        {
                            clearTimeout(xhrtimer);

                            switch(xhr.status)
                            {
                                case 200:
                                    var res = xhr.response;

                                    if(options.console)
                                        console.log("[Xirvik] checking promos, server response: " + res);

                                    if(res)
                                    {
                                        var obj = JSON.parse(res);

                                        if(window.confirm(obj.body))
                                        {
                                            chrome.tabs.create({'url': obj.url}, function(tab1) {});
                                        }
                                    }
                            }
                        }
                    };

                    xhr.send();

                    xhrtimer = setTimeout(function()
                    {
                        if(options.console)
                            console.log("[Xirvik] checking promos, timeout error.");

                        xhr.abort();
                        delete xhr;
                    },
                    options.timeout * 1000);

                }
            }

            function checkLabelsAndDirs(senderId, server, callback)
            {
                if(options.console)
                    console.log("[Xirvik] Checking labels/dirs.");

                var labels_ = null, dirs_ = [];
                var label = null, directory = null;

                if(((server.client == "rutorrent 3.x") || (server.client == "rutorrent 2.x")) && (options.labels || options.dirs))
                {
					var modes = [];

					if(options.dirs)
						modes.push("dirlist");

					if(options.labels)
						modes.push("labels");

                    var url = server.host;

                    if(url.charAt(url.length - 1) != "/")
                        url += "/";

					url += "plugins/_getdir/info.php?mode=" + modes.join(";");

                    if(options.console)
                        console.log("[Xirvik] Rutorrent - checking labels/dirs, calling " + url + ".");

                    var xhr = new XMLHttpRequest(), xhrtimer = null;
                    xhr.open('GET', url, true, server.user, server.pass);

                    xhr.onreadystatechange = function(res)
                    {
                        if(xhr.readyState == 4)
                        {
                            clearTimeout(xhrtimer);

                            switch(xhr.status)
                            {
                                case 200:
                                    var res = xhr.response;

                                    if(options.console)
                                        console.log("[Xirvik] Rutorrent - checking labels/dirs, server response: " + res);

                                    if(res)
                                    {
                                        var obj = JSON.parse(res.replace("labels:", "\"labels\":").replace("basedir:", "\"basedir\":").replace("dirlist:", "\"dirlist\":").replace(/'/g, "\""));

                                        if(obj.labels)
                                            labels_ = obj.labels;

                                        if(obj.basedir)
                                        {
                                            base = obj.basedir;

                                            if(base.charAt(base.length - 1) != "/")
                                                base += "/";
                                        }

                                        if(obj.dirlist)
                                        {
                                            for(var i = 0; i < obj.dirlist.length; i++)
                                            {
                                                var dir = obj.dirlist[i];
                                                if(dir == "..")
                                                {
                                                    continue;
                                                }
                                                else if(dir == ".")
                                                {
                                                    dirs_.push("(root directory)");
                                                }
                                                else
                                                    dirs_.push(dir);
                                            }
                                        }

                                        if(options.labels && options.dirs)
                                        {
                                            chrome.tabs.sendMessage(senderId, { dialog: "labeldirectory", directories: dirs_, labels: labels_ }, function (response)
                                            {
                                                if(options.console)
                                                    console.log("[Xirvik] Rutorrent - checking labels/dirs, user response: " + response.label + ", " + response.directory);

                                                if(callback && response && response.label && response.directory)
                                                    callback(response.label, base + response.directory);
                                            });
                                        }
                                        else
                                        {
                                            if(options.labels)
                                            {
                                                chrome.tabs.sendMessage(senderId, { dialog: "label", labels: labels_ }, function (response)
                                                {
                                                    if(options.console)
                                                        console.log("[Xirvik] Rutorrent - checking labels/dirs, user response: " + response.label);

                                                    if(callback && response && response.label)
                                                        callback(response.label);
                                                });
                                            }
                                            else if(options.dirs)
                                            {
                                                chrome.tabs.sendMessage(senderId, { dialog: "directory", directories: dirs_ }, function (response)
                                                {
                                                    if(options.console)
                                                        console.log("[Xirvik] Rutorrent - checking labels/dirs, user response: " + response.directory);

                                                    if(callback && response && response.directory)
                                                        callback(null, base + response.directory);
                                                });
                                            }
                                        }
                                    }
                                    break;

                                default:
                                    if(options.console)
                                        console.log("[Xirvik] Rutorrent - checking labels/dirs failed.");

                                    if(options.messagesf)
                                        showNotification('Timeout', 'Label info download failed because of seedbox error (HTTP ' + xhr.status + ').');
                            }
                        }
                    };

                    xhr.send();

                    xhrtimer = setTimeout(function()
                    {
                        if(options.console)
                            console.log("[Xirvik] Rutorrent - checking labels/dirs, timeout error.");

                        xhr.abort();
                        delete xhr;

                        if(options.messagest)
                            showNotification('Timeout', 'Label info download failed because of seedbox timeout.');
                    },
                    options.timeout * 1000);
                }
                else
                {
                    if(callback)
                        callback();
                }
            }

            chrome.extension.onRequest.addListener(
                function(request, sender, sendResponse)
                {
                    if(request.options)
                    {
                        if(options.console)
                        {
                            console.log("[Xirvik] Storing options:");
                            console.log(request.options);
                        }

                        options = request.options;
                        setItem("options", JSON.stringify(request.options));
                        sendResponse({});
                        return;
                    }

                    if(request.getoptions)
                    {
                        if(options.console)
                        {
                            console.log("[Xirvik] Requesting options:");
                            console.log(options);
                        }

                        sendResponse({options: options});
                        return;
                    }

                    function upload(url, server)
                    {
                        if(options.console)
                            console.log("[Xirvik] Transferring torrent from: " + url);

                                checkLabelsAndDirs(sender.tab.id, server, function(label, directory)
                                {
                                    if((url.indexOf("magnet:") == 0) && ((server.client == "rutorrent 3.x") || (server.client == "rutorrent 2.x")))
                                    {
                                        if(options.console)
                                            console.log("[Xirvik] Magnet link from: " + url);

                                        var url_ = server.host;

                                        if(url_.charAt(url_.length - 1) != "/")
                                            url_ += "/";

                                        switch(server.client)
                                        {
                                            case "rutorrent 3.x":
                                                url_ += "php/";

                                            case "rutorrent 2.x":
                                                url_ += "addtorrent.php?";
                                        }

                                        if(options.console)
                                            console.log("[Xirvik] Magnet link from: " + url_);

                                        var more = [];
                                        var formData = new FormData();
                                        formData.append("url", url);

                                        // Construct file to upload:
                                        formData.append("dir_edit", (directory && directory.length) ? directory : "");

                                        if(options.nostart)
                                        {
                                            formData.append("torrents_start_stopped", "on");
                                            more.push("torrents_start_stopped=1");
                                        }

                                        formData.append("tadd_label", (label && label.length) ? label : "");

                                        if(label && label.length)
                                            more.push("label=" + label);

                                        if(more.length)
                                            url_ += more.join("&");

                                        if(options.messageus)
                                            showNotification('Uploading', 'Starting torrent upload to seedbox.');

                                        var xhr2 = new XMLHttpRequest(), xhr2timer = null;
                                        xhr2.open('POST', url_, true, server.user, server.pass);

                                        xhr2.onreadystatechange = function()
                                        {
                                            if(xhr2.readyState == 4)
                                            {
                                                clearTimeout(xhr2timer);

                                                switch(xhr2.status)
                                                {
                                                    case 200:
                                                        if(options.console)
                                                            console.log("[Xirvik] Magnet link uploaded successfully.");

                                                        if(options.messageuc)
                                                            showNotification('Uploaded', 'Torrent uploaded successfully.');

                                                        break;

                                                    case 401:
                                                    case 403:
                                                    case 407:
                                                        if(options.console)
                                                            console.log("[Xirvik] Magnet link uploading - seedbox authentication failed.");

                                                        if(options.messagesf)
                                                            showNotification('Failure', 'Server authentication failed.');

                                                        break;

                                                    default:
                                                        if(options.console)
                                                            console.log("[Xirvik] Magnet link uploading failed (HTTP " + xhr2.status + ").");

                                                        if(options.messageuf)
                                                            showNotification('Failure', 'Torrent upload failed (HTTP ' + xhr2.status + ').');

                                                        break;
                                                }
                                            }
                                        };

                                        xhr2.send(formData);

                                        xhr2timer = setTimeout(function()
                                        {
                                            if(options.console)
                                                console.log("[Xirvik] Magnet uploading timeout.");

                                            xhr2.abort();
                                            delete xhr2;

                                            if(options.messagest)
                                                showNotification('Timeout', 'Timeout uploading torrent.');
                                        },
                                        options.timeout * 1000);

                                        return;
                                    }

                                    if(options.messageds)
                                        showNotification('Downloading', 'Starting torrent download.');

                                    if(options.console)
                                        console.log("[Xirvik] Downloading from:" + url);

                                    var xhr = new XMLHttpRequest(), xhrtimer = null;
                                    xhr.overrideMimeType("application/octet-stream");

                                    xhr.open("GET", url, true);
                                    xhr.responseType = "arraybuffer";

                                    xhr.onreadystatechange = function()
                                    {
                                        if(xhr.readyState == 4)
                                        {
                                            clearTimeout(xhrtimer);

                                            if(xhr.status == 200)
                                            {
                                                var res = xhr.response;

                                                if(options.console)
                                                    console.log("[Xirvik] Download response:" + res);

                                                if(res)
                                                {
                                                    var byteArray = new Uint8Array(res);
                                                    var dataView = new DataView(byteArray.buffer);
                                                    var blob = new Blob([dataView], {type: "application/octet-stream"});

                                                    var formData = new FormData();
                                                    url = server.host;

                                                    if(url.charAt(url.length - 1) != "/")
                                                        url += "/";

                                                    switch(server.client)
                                                    {
                                                        case "rutorrent 3.x":
                                                            url += "php/";

                                                        case "rutorrent 2.x":
                                                            url += "addtorrent.php?";

                                                            if(options.console)
                                                                console.log("[Xirvik] Uploading to: " + url);

                                                            var more = [];

                                                            // Construct file to upload:
                                                            formData.append("dir_edit", (directory && directory.length) ? directory : "");

                                                            if(options.nostart)
                                                            {
                                                                formData.append("torrents_start_stopped", "on");
                                                                more.push("torrents_start_stopped=1");
                                                            }

                                                            formData.append("tadd_label", (label && label.length) ? label : "");

                                                            if(label && label.length)
                                                                more.push("label=" + label);

                                                            if(more.length)
                                                                url += more.join("&");

                                                            formData.append("torrent_file", blob);
                                                        break;

                                                        case "utorrent":
                                                            url += "?action=add-file";

                                                            if(options.console)
                                                                console.log("[Xirvik] Uploading to: " + url);

                                                            formData.append("torrent_file[]", blob);
                                                            break;

                                                        case "torrentflux-b4rt":
                                                            url += "dispatcher.php?action=fileUpload";

                                                            if(options.console)
                                                                console.log("[Xirvik] Uploading to: " + url);

                                                            formData.append("aid", "2");
                                                            formData.append("client", "torrentflux-b4rt");
                                                            formData.append("tadd_label", "");
                                                            formData.append("upload_files[]", blob);
                                                            break;

                                                        case "deluge":
                                                            if(options.messageus)
                                                                showNotification('Uploading', 'Starting torrent upload to seedbox.');

                                                            var postData = "{\"method\":\"auth.login\",\"params\":[\"deluge\"],\"id\":2}";

                                                            var xhr2 = new XMLHttpRequest(), xhr2timer = null;
                                                            xhr2.setRequestHeader("Content-Type", "application/json; charset=UTF-8");
                                                            xhr2.setRequestHeader("X-Requested-With", "XMLHttpRequest");
                                                            xhr2.setRequestHeader("Referer", url);
                                                            xhr2.setRequestHeader("Content-Length", postData.length);

                                                            if(options.console)
                                                                console.log("[Xirvik] Uploading to: " + url + "json");

                                                            xhr2.open('POST', url + "json", true, server.user, server.pass);

                                                            xhr2.onreadystatechange = function()
                                                            {
                                                                if(xhr2.readyState == 4)
                                                                {
                                                                    clearTimeout(xhr2timer);

                                                                    if(xhr2.status == 200)
                                                                    {
                                                                        if(options.console)
                                                                            console.log("[Xirvik] Uploading to: " + url + "upload");

                                                                        var xhr3 = new XMLHttpRequest();
                                                                        xhr3.open('POST', url + "upload", true, server.user, server.pass);

                                                                        formData.append("file", blob);

                                                                        xhr3.onreadystatechange = function()
                                                                        {
                                                                            if(xhr3.readyState == 4)
                                                                            {
                                                                                if(xhr3.status == 200)
                                                                                {
                                                                                    var res = xhr3.response;

                                                                                    if(options.console)
                                                                                        console.log("[Xirvik] Deluge step 2 response: " + res);

                                                                                    if(res)
                                                                                    {
                                                                                        var response = JSON.parse(res);
                                                                                        var path = response["files"][0];

                                                                                        // Post message:
                                                                                        postdata = "{\"method\":\"web.add_torrents\",\"params\":[[{\"path\":\"" + path + "\",\"options\":{\"file_priorities\":[1,1],\"add_paused\":" + (that.branch.getBoolPref("nostart") ? "true" : "false") + ",\"compact_allocation\":false,\"download_location\":\"/torrents/" + server[1] + "\",\"max_connections\":-1,\"max_download_speed\":-1,\"max_upload_slots\":-1,\"max_upload_speed\":-1,\"prioritize_first_last_pieces\":false}}]],\"id\":155}";

                                                                                        var xhr4 = new XMLHttpRequest(), xhr4timer = null;
                                                                                        xhr4.setRequestHeader("Content-Type", "application/json; charset=UTF-8");
                                                                                        xhr4.setRequestHeader("X-Requested-With", "XMLHttpRequest");
                                                                                        xhr4.setRequestHeader("Referer", url);
                                                                                        xhr4.setRequestHeader("Content-Length", postData.length);

                                                                                        xhr4.open('POST', url + "json", true, server.user, server.pass);

                                                                                        xhr4.onreadystatechange = function()
                                                                                        {
                                                                                            if(xhr4.readyState == 4)
                                                                                            {
                                                                                                clearTimeout(xhr4timer);

                                                                                                if(xhr4.status == 200)
                                                                                                {
                                                                                                    if(options.console)
                                                                                                        console.log("[Xirvik] Deluge, torrent uploaded successfully");

                                                                                                    if(options.messageuc)
                                                                                                        showNotification('Uploaded', 'Torrent uploaded successfully.');
                                                                                                }
                                                                                                else if((xhr4.status == 401) || (xhr4.status == 403) || (xhr4.status == 407))
                                                                                                {
                                                                                                    if(options.console)
                                                                                                        console.log("[Xirvik] Deluge, server authentication failed.");

                                                                                                    if(options.messagesf)
                                                                                                        showNotification('Failure', 'Server authentication failed.');
                                                                                                }
                                                                                                else
                                                                                                {
                                                                                                    if(options.console)
                                                                                                        console.log("[Xirvik] Deluge, torrent upload failed (HTTP " + xhr4.status + ")..");

                                                                                                    if(options.messageuf)
                                                                                                        showNotification('Failure', 'Torrent upload failed (HTTP ' + xhr4.status + ').');
                                                                                                }
                                                                                            }
                                                                                        };

                                                                                        xhr4.send(postdata);

                                                                                        xhr4timer = setTimeout(function()
                                                                                        {
                                                                                            if(options.console)
                                                                                                console.log("[Xirvik] Deluge, timeout uploading torrent.");

                                                                                            xhr4.abort();
                                                                                            delete xhr4;

                                                                                            if(options.messageuf)
                                                                                                showNotification('Timeout', 'Timeout uploading torrent.');
                                                                                        },
                                                                                        options.timeout * 1000);
                                                                                    }
                                                                                }
                                                                                else if((xhr3.status == 401) || (xhr3.status == 403) || (xhr3.status == 407))
                                                                                {
                                                                                    if(options.console)
                                                                                        console.log("[Xirvik] Deluge, server authentication failed.");

                                                                                    if(options.messagesf)
                                                                                        showNotification('Failure', 'Server authentication failed.');
                                                                                }
                                                                                else
                                                                                {
                                                                                    if(options.console)
                                                                                        console.log("[Xirvik] Deluge, torrent upload failed (HTTP " + xhr3.status + ")..");

                                                                                    if(options.messageuf)
                                                                                        showNotification('Failure', 'Torrent upload failed (HTTP ' + xhr3.status + ').');
                                                                                }
                                                                            }
                                                                        };

                                                                        xhr3.send(formData);
                                                                    }
                                                                    else if((xhr2.status == 401) || (xhr2.status == 403) || (xhr2.status == 407))
                                                                    {
                                                                        if(options.console)
                                                                            console.log("[Xirvik] Deluge, server authentication failed.");

                                                                        if(options.messagesf)
                                                                            showNotification('Failure', 'Server authentication failed.');
                                                                    }
                                                                    else
                                                                    {
                                                                        if(options.console)
                                                                            console.log("[Xirvik] Deluge, torrent upload failed (HTTP " + xhr2.status + ")..");

                                                                        if(options.messageuf)
                                                                            showNotification('Failure', 'Torrent upload failed (HTTP ' + xhr2.status + ').');
                                                                    }
                                                                }
                                                            };

                                                            xhr2.send(postData);

                                                            xhr2timer = setTimeout(function()
                                                            {
                                                                if(options.console)
                                                                    console.log("[Xirvik] Deluge, timeout uploading torrent.");

                                                                xhr2.abort();
                                                                delete xhr2;

                                                                if(options.messageuf)
                                                                    showNotification('Timeout', 'Timeout uploading torrent.');
                                                            },
                                                            options.timeout * 1000);

                                                            return;
                                                    }

                                                    if(options.messageus)
                                                        showNotification('Uploading', 'Starting torrent upload to seedbox.');

                                                    var xhr2 = new XMLHttpRequest(), xhr2timer = null;;
                                                    xhr2.open('POST', url, true, server.user, server.pass);

                                                    xhr2.onreadystatechange = function()
                                                    {
                                                        if(xhr2.readyState == 4)
                                                        {
                                                            clearTimeout(xhr2timer);
                                                            delete blob;

                                                            if(xhr2.status == 200)
                                                            {
                                                                if(options.console)
                                                                    console.log("[Xirvik] Torrent uploaded successfully.");

                                                                if(options.messageuc)
                                                                    showNotification('Uploaded', 'Torrent uploaded successfully.');
                                                            }
                                                            else if((xhr2.status == 401) || (xhr2.status == 403) || (xhr2.status == 407))
                                                            {
                                                                if(options.console)
                                                                    console.log("[Xirvik] Server authentication failed.");

                                                                if(options.messagesf)
                                                                    showNotification('Failure', 'Server authentication failed.');
                                                            }
                                                            else
                                                            {
                                                                if(options.console)
                                                                    console.log("[Xirvik] Torrent upload failed (HTTP " + xhr2.status + ")..");

                                                                if(options.messageuf)
                                                                    showNotification('Failure', 'Torrent upload failed (HTTP ' + xhr2.status + ').');
                                                            }
                                                        }
                                                    };

                                                    xhr2.send(formData);

                                                    xhr2timer = setTimeout(function()
                                                    {
                                                        if(options.console)
                                                            console.log("[Xirvik] Timeout uploading torrent.");

                                                        xhr2.abort();
                                                        delete xhr2;

                                                        if(options.messageuf)
                                                            showNotification('Timeout', 'Timeout uploading torrent.');
                                                    },
                                                    options.timeout * 1000);
                                                }

                                                delete xhr;
                                            }
                                            else
                                            {
                                                if(options.console)
                                                    console.log("[Xirvik] Torrent download failed (HTTP " + xhr.status + ")..");

                                                if(options.messagedf)
                                                    showNotification('Failure', 'Torrent download failed (HTTP ' + xhr.status + ').');
                                            }
                                        }
                                    };

                                    xhr.send(null);

                                    xhrtimer = setTimeout(function()
                                    {
                                        if(options.console)
                                            console.log("[Xirvik] Torrent download failed because of source server timeout.");

                                        xhr.abort();
                                        delete xhr;

                                        if(options.messagedf)
                                            showNotification('Timeout', 'Torrent download failed because of source server timeout.');
                                    },
                                    options.timeout * 1000);
                                });
                    }

                    if((options.click && request.click) || (request.force && request.click))
                    {
                        var url = request.click;

                        if(options.console)
                            console.log("[Xirvik] Click detected: " + url);

                        url = (request.force || ((url.indexOf(".torrent") != -1) || (url.indexOf("magnet:") == 0))) ? url : null;

                        if(!url)
                            return;

                        if(options.console)
                            console.log("[Xirvik] Click is ok for download: " + url);

                        if(options.servers.length > 1)
                        {
                            chrome.tabs.sendMessage(sender.tab.id, { dialog: "list", choices: options.servers }, function (response)
                            {
                                var server = options.servers[response.choice];

                                upload(url, server);
                            });
                        }
                        else if(options.servers.length == 1)
                        {
                            var server = options.servers[0];

                            upload(url, server);
                        }
                        return;
                    }

                    chrome.contextMenus.removeAll();

                    var url = request.url;

                    if(!url)
                        return;

                    if(!options.capture)
                        url = ((url.indexOf(".torrent") != -1) || (url.indexOf("magnet:") == 0)) ? url : null;

                    if(url)
                    {
                        if(options.console)
                            console.log("[Xirvik] Processing link: " + url);

                        var single = (options.servers.length == 1);

                        function createContextItem(index)
                        {
                            var server = options.servers[index], shortname = server.host;

                            if(shortname.indexOf("http://") != -1)
                                shortname = shortname.substr("http://".length);
                            else if(shortname.indexOf("https://") != -1)
                                shortname = shortname.substr("https://".length);

                            chrome.contextMenus.create({type: "normal", title: (single ? "Upload to " : "") + shortname + " (" + server.client + ")", contexts: ["link"], parentId: root, onclick: function()
                            {
                                upload(url, server);
                            }});
                        }

                        if(single)
                        {
                            createContextItem(0);
                        }
                        else
                        {
                            var root = chrome.contextMenus.create({type: "normal", title: "Upload to Xirvik seedbox", contexts: ["link"]}, function()
                            {
                                for(var i = 0; i < options.servers.length; i++)
                                {
                                    createContextItem(i);
                                }
                            });
                        }
                    }

                    sendResponse({});
                }
            );

            /* Server autoconfig: */

            var handleDouble = false;

            var configHandler = function(details)
            {
                if(handleDouble)
                    return;

                if(options.console)
                    console.log("[Xirvik] Autoconfig - initial checks.");

                handleDouble = true;

                var url = details.url, type = "", user = null, pass = null;

                for(var i = 0, iLimit = details.responseHeaders.length; i < iLimit; i++)
                {
                    var header = details.responseHeaders[i];

                    switch(header.name)
                    {
                        case "Content-Type":
                            type = header.value;
                            break;

                        case "Authorization-echo":
                            var loginstr = base64decoder.decodeString(header.value);

                            if(loginstr && loginstr.length && (loginstr.indexOf(":") != -1))
                            {
                                loginarr = loginstr.split(":");
                                user = loginarr[0];
                                pass = loginarr[1];
                            }

                            break;
                    }
                }

                if((type == "application/seedboxconfig") && user && pass)
                {
                    if(options.console)
                        console.log("[Xirvik] Autoconfig in progress.");

                    // make a call to url once again to retrieve the XML:
                    var xhr = new XMLHttpRequest();
                    xhr.open('GET', url, true);
                    xhr.overrideMimeType('text/xml');

                    xhr.onreadystatechange = function(response)
                    {
                        if((xhr.readyState == 4) && (xhr.status == 200))
                        {
                            var xml = response.target.responseXML;

                            if(xml)
                            {
                                xml = xml.documentElement;

                                // Check autoconf xml for validity:
		                        if((xml.nodeName == "autoconf") && (xml.getAttribute("name") == "xirvik"))
		                        {
			                        var servers = xml.getElementsByTagName("server"), success = 0;

                                    // Cycle through all the seedboxes in the autoconf file:
			                        for(var i = 0; i < servers.length; i++)
			                        {
				                        var server = servers[i];
				                        var optiontags = server.getElementsByTagName("option");

				                        var host = "", username = "", passwd = "", description = "", client = "";

                                        // Get seedbox data:
				                        for(var k = 0; k < optiontags.length; k++)
				                        {
					                        var option = optiontags[k], value = option.getAttribute("value");

					                        switch(option.getAttribute("name"))
					                        {
						                        case "host":
							                        host = value;
							                        break;

						                        case "username":
							                        username = value;
							                        break;

						                        case "pass":
							                        passwd = value;
							                        break;

						                        case "description":
							                        description = value;
							                        break;

						                        case "client":
							                        client = value;
							                        break;
					                        }
				                        }

				                        // Check for path validity:
				                        var tmphost = host;

                                        if(!tmphost.length || (tmphost == "/") || (tmphost == "\\"))
                                        {
                                            if(!window.confirm("Seedbox [" + host + "] doesn't seem to contain the correct path. Are you sure you want to continue with it?"))
                                            {
                                                return;
                                            }
                                        }

                                        if(!i)
                                        {
                                            // Check if host info already exists in extension options - only for 1st entry:
                                            var found = false;

                                            for(var j = 0; j < options.servers.length; j++)
                                            {
                                                if(options.servers[j].host.indexOf(tmphost) != -1)
                                                {
                                                    found = true;
                                                    break;
                                                }
                                            }

                                            if(found)
                                            {
                                                if(!window.confirm("Seedboxes' data for [" + tmphost + "] were found in your Xirvik preferences.\nAre you sure you want to rewrite them with the new ones?"))
                                                {
                                                    return;
                                                }

                                                // Found (at least a single) host already in preferences - wipe out this server.
                                                tmphost = tmphost.substring(tmphost.indexOf("://"), tmphost.lastIndexOf("/"));

                                                for(var j = 0; j < options.servers.length; j++)
                                                {
                                                    if(options.servers[j].host.indexOf(tmphost) != -1)
                                                    {
                                                        options.servers.splice(j, 1);
                                                        j--;
                                                    }
                                                }
                                            }
                                        }

				                        if(!username)
				                        {
					                        if(user && user.length)
					                        {
						                        username = user;
					                        }
				                        }

				                        if(!passwd)
				                        {
					                        if(pass && pass.length)
					                        {
						                        passwd = pass;
					                        }
				                        }

				                        // Add server to server data:
                                        options.servers.push({pass: passwd,
                                                            descr: description,
                                                            host: host,
                                                            user: username,
                                                            client: client});

				                        success++;
			                        }

                                    if(success)
                                    {
                                        setItem("options", JSON.stringify(options));
                                    }
                                }

                                handleDouble = false;
                            }
                        }
                    }

                    xhr.send(null)
                }
            };

            var filter = {urls: ["*://*.xirvik.com/browsers_addons/get_addon_config.php"]};
            var opt_extraInfoSpec = ["responseHeaders"];

            chrome.webRequest.onHeadersReceived.addListener(configHandler, filter, opt_extraInfoSpec);

            var torrentHandler = function(details)
            {
                var isfile = false;

                for(var i = 0, iLimit = details.responseHeaders.length; i < iLimit; i++)
                {
                    var header = details.responseHeaders[i];

                    switch(header.name)
                    {
                        case "Content-Type":
                            isfile = isfile || (header.value.indexOf("application/x-bittorrent") != -1);
                            break;

                        case "Content-Disposition":
                            isfile = isfile || (header.value.indexOf(".torrent") != -1);
                            break;
                    }
                }

                if(isfile && (details.type != "xmlhttprequest") && (typeof details.tabId != "undefined"))
                {
                    if(options.console)
                        console.log("[Xirvik] Torrent capture in progress.");

                    chrome.tabs.query({lastFocusedWindow: true, active: true}, function(tabs)
                    {
                        if(tabs && tabs.length)
                            chrome.tabs.sendMessage(tabs[0].id, { echo: details.url }, function (response) { });
                    });
                }
            };

            chrome.webRequest.onHeadersReceived.addListener(torrentHandler, {urls: ["*://*/*"]}, opt_extraInfoSpec);

            /* Helper base64 decoder: */

            function G_Base64() {
              this.byteToCharMap_ = {};
              this.charToByteMap_ = {};
              this.byteToCharMapWebSafe_ = {};
              this.charToByteMapWebSafe_ = {};
              this.init_();
            }

            G_Base64.ENCODED_VALS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ" +
                                    "abcdefghijklmnopqrstuvwxyz" +
                                    "0123456789+/=";

            G_Base64.ENCODED_VALS_WEBSAFE = "ABCDEFGHIJKLMNOPQRSTUVWXYZ" +
                                            "abcdefghijklmnopqrstuvwxyz" +
                                            "0123456789-_=";

            G_Base64.prototype.init_ = function() {
              for (var i = 0; i < G_Base64.ENCODED_VALS.length; i++) {
                this.byteToCharMap_[i] = G_Base64.ENCODED_VALS.charAt(i);
                this.charToByteMap_[this.byteToCharMap_[i]] = i;
                this.byteToCharMapWebSafe_[i] = G_Base64.ENCODED_VALS_WEBSAFE.charAt(i);
                this.charToByteMapWebSafe_[this.byteToCharMapWebSafe_[i]] = i;
              }
            }

            G_Base64.prototype.decodeString = function(input, opt_webSafe) {

              if (input.length % 4)
                throw new Error("Length of b64-encoded data must be zero mod four");

              var charToByteMap = opt_webSafe ? 
                                  this.charToByteMapWebSafe_ :
                                  this.charToByteMap_;

              var output = "";

              var i = 0;
              while (i < input.length) {

                var byte1 = charToByteMap[input.charAt(i)];
                var byte2 = charToByteMap[input.charAt(i + 1)];
                var byte3 = charToByteMap[input.charAt(i + 2)];
                var byte4 = charToByteMap[input.charAt(i + 3)];

                if (byte1 === undefined || byte2 === undefined ||
                    byte3 === undefined || byte4 === undefined)
                  throw new Error("String contains characters not in our alphabet: " + input);

                var outByte1 = (byte1 << 2) | (byte2 >> 4);
                output += String.fromCharCode(outByte1);

                if (byte3 != 64) {
                  var outByte2 = ((byte2 << 4) & 0xF0) | (byte3 >> 2);
                  output += String.fromCharCode(outByte2);

                  if (byte4 != 64) {
                    var outByte3 = ((byte3 << 6) & 0xC0) | byte4;
                    output += String.fromCharCode(outByte3);
                  }
                }

                i += 4;
              }

              return output;
            }

            var base64decoder = new G_Base64();

window.addEventListener("load", function() { load(); }, false);