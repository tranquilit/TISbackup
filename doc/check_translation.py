import fnmatch
import os

matches = []
for root, dirnames, filenames in os.walk('source/locale/fr/LC_MESSAGES/'):
    for filename in fnmatch.filter(filenames, '*.po'):
        filename = os.path.join(root, filename)
        matches.append(os.path.join(root, filename))
        data = open(filename,'r').readlines()
        val = 0
        linenumber = 1
        for line in data:
            if line.startswith('msgstr ""'):
                val = 1
                continue
            if line.strip()=='' and val==1:
                print( "empty translation line %s in %s" % (linenumber,filename))
            val = 0
            if line.startswith('#, fuzzy'):
                print ("fuzzy line %s in %s " % (linenumber,filename))
            linenumber = linenumber + 1
