# BETA! Use art your own risk

# Volund's Athanor Framework for Evennia

## CONTACT INFO
**Name:** Volund

**Email:** volundmush@gmail.com

**PayPal:** volundmush@gmail.com

**Discord:** Volund#1206

**Patreon:** https://www.patreon.com/volund

**Home Repository:** https://github.com/volundmush/athanor

## TERMS AND CONDITIONS

BSD license. Please see the included LICENSE.txt for the legalese.

In short:
Go nuts. Use this code however you like. Modify it and distribute such modifications to your heart's content. Heck, you can even run a commercial game with paid services and microtransactions. Whatever. But give credit where credit is due. (me, and Evennia's original coders). And if you DO make money off of it, please be awesome and support me on Patreon!

Support is limited by my time, energy, and funds. No guarantees can be made, but I love to see quality stuff out there.

If you fix any bugs with your own projects, I'd __really__ appreciate some fix contributions.

## REQUIREMENTS
  * A reliable server host. Most managed MUD hosting solutions won't cut it, as the base library (Evennia) requires far more RAM and CPU than old CircleMUD, DikuMUD, PennMUSH, etc.
  * Decent computer administration skills and minor familiarity with coding. Failing that, the spirit to try anyways. Get messy. Make a few mistakes, maybe? Setting up Athanor requires modifying a few .py files while obeying syntax rules. It may also require you to configure port forwarding settings, work with webserver configurations, and whatever other complications your hosting introduces.
  * Evennia 0.9 running on Python 3.8. Might work with newer versions too! Try it.

## DESIGN FEATURES
  * **MODULARITY:** Install only the features you want. The CORE is designed to elegantly co-exist with Evennia and a 'mygame'. Make a MUD, a MUSH-like experience, whatever you want! You can replace, sub-class, and add to basically any component. Creating your own Athanor Plugin, or adding any of those provided on git is fairly simple.

  * **API BASED:** All operations from displaying a WHO list to logging in are handled through API calls to CONTROLLER singletons. This API is designed with GMCP/OOB/MSDP in mind so that clients and the server can communicate via quiet JSON messages to each other. In short, it's made with amazing WebClients and MUSHclient plugins that provide GUI features in mind.

  * **CONFIGURABILITY:** Plugins are designed to be easily configured through edits to your settings.py file.

  * **ACCOUNT-BASED CHARACTER/ALTS MANAGEMENT:** Athanor takes full advantage of Evennia's MULTISESSION_MODEs 2 and 3, meant to present itself similar to modern MMORPGs.

## INSTALLATION GUIDE
  1. Install Evennia. If you don't know how, I'd suggest checking out https://github.com/evennia/evennia/wiki/Getting-Started
  2. Download-and-extract or clone this repository. (I recommend using git so you can update!) install using `pip install -e athanor` just like with Evennia.
  3. Create your GameDir using the `evennia --init mygame` command where you want it.
  4. in your `<gamedir/server/conf/settings.py` file... replace `from evennia.settings_default import *` with `from athanor.athanor_settings import *`
  5. Create a `<gamedir>/server/conf/plugin_settings.py` file.
  6. Follow the install instructions for the plugins you'd like to use. This is usually as simple as adding to `ATHANOR_PLUGINS` in the plugin_settings.py file.
  7. Remember to `evennia makemigrations` and `evennia migrate` before you `evennia start` !


## FAQ
  __Q:__ Why 'Athanor' for a name?  
  __A:__ Well, I had to call it something. This is a transformative project that refines Evennia into something that more suits my style, but isn't itself a game. It's the intermediary through which the magic happens. So I named it after the classical Alchemist's furnace.

  __Q:__ Where can I get more Plugins?  The default ones aren't enough!
  __A:__ From my GitHub! See anything starting with athanor_* at https://github.com/volundmush - and, failing that...

  __Q:__ How do I make my own Plugins?  
  __A:__ Hope you've got some Python skills. Really, download one of mine and tear it apart. `athanor_forum` is a good start.
  
  __Q:__ Can I install Athanor on an already-existing Evennia game?  
  __A:__ It is designed to be installed from the very start of an Evennia project. An existing project may need custom database migrations and code refactoring that I probably can't help you with.
  
  __Q:__ This is cool! How can I help?  
  __A:__ Patreon support is always welcome. If you can code and have cool ideas or bug fixes, feel free to fork, edit, and pull request!

  __Q:__ I found a bug! What do I do?  
  __A:__ Post it on this GitHub's Issues tracker. I'll see what I can do when I have time. ... or you can try to fix it yourself and submit a Pull Request. That's cool too.

  __Q:__ I want to add a new feature! What do I do?  
  __A:__ Adding new features to the Athanor Core isn't really how this works. That's what Plugins are for. Still, a Feature Request or Pull Request via GitHub is always welcome.

## Special Thanks
  * The Evennia team, especially Griatch, for guiding me this far.
  * All of my Patrons on Patreon.