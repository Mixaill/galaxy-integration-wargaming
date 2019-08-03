# galaxy-integration-wargaming
GOG Galaxy 2.0 Wargaming Game Center integration

## Installation

* Clone repository to `%localappdata%\GOG.com\Galaxy\plugins\installed\wargaming\`

## Limitations

* Only World of Tanks friends and chat is supported
* No friends and chat roaming between realms

## Changelog

* v. 0.7.3
   * updated Galaxy API to 0.46
   * fixed connection to WGC servers for NA region 

* v. 0.7.2
   * updated Galaxy API to 0.43
   * fixed incorrect game state update on game launch
   * fixed requests to WG.net server when WGC is not installed

* v. 0.7.1
   * updated Galaxy API to 0.42
   * fixed incorrect variable name in `wgc_api::wguscs_get_showroom()`
   * fixed exception on cancelled `asyncio.sleep()`
   * fixed region handling in `PAPIWoT::get_account_info()` request

* v. 0.7.0
   * implemented receiving friends list
   * implemented receiving user info
   * improved error handling when servers are not responsible
   * fixed error on retrieving WGC settings when WGC is not installed

* v. 0.6.0
   * Implemented ability to install games. Ability to install games is implemented. Now this integration implements a minimal set of functions for everyday use!
   * Implemented login via OTP backup codes
   * Fixed exception in `get_owned_games()` function
   * Updated Sentry SDK to 0.10.0

* v. 0.5.0
   * Fetch owned games from Wargaming.net account

* v. 0.4.5
   * Improve Wargaming.net authorization error processing

* v. 0.4.4
   * Galaxy SDK updated to 0.40.1
   * Fixed exception when there is no installed games
   * Added error logging via Sentry

* v. 0.4.3
   * implemented two factor authorization
   * Galaxy SDK updated to 0.38

* v. 0.4.2
   * changed nickname format from `<email>` to `<realm>_<nickname>`

* v. 0.4.1
   * fixed Wargaming.net authorization on non-RU realms
   * added additional authorization logging

* v. 0.4.0
   * implemented Wargaming.net authorization

* v. 0.3.0
   * add ability to delete games

* v. 0.2.0
   * added detection that the game is running.

* v. 0.1.0
   * initial release

## Additional info

* GOG Galaxy Integrations API: https://github.com/gogcom/galaxy-integrations-python-api
* Go-WgAuth library by Renat Iliev (@IzeBerg): https://bitbucket.org/The_IzeBerg/go-wgauth/

