# galaxy-integration-wargaming
GOG Galaxy 2.0 Wargaming Game Center integration

## Installation

* Clone repository to `%localappdata%\GOG.com\Galaxy\plugins\installed\wargaming\`

## Changelog

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

