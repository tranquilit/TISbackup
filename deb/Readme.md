Once the deb package is created, one can use it to install tisbackup on a debian machine with python3. The command is:  
```
    apt install ./tis-tisbackup-1-2-0.151-deb11.deb
```  
Note that the version numbers might be different depending on the system you used to build the package.

After this, one have to generate the public and private certificates, as root:  
```
    cd
    ssh-keygen -t rsa -b 2048
```  
(press enter for each step)

Then propagate the public certificate on the machines targetted for backup:  
```
    ssh-copy-id -i /root/.ssh/id_rsa.pub root@machine1
    ssh-copy-id -i /root/.ssh/id_rsa.pub root@machine2
```  
etc.

Configure your backup jobs:  
```
    cd /etc/tis
    cp tisbackup-config.ini.sample tisbackup-config.ini
    vi tisbackup-config.ini
```  

Eventually modify ```/etc/cron.d/tisbackup``` for your needs.

Finalize the installation with:  
```
    tisbackup -d backup
    systemctl enable tisbackup_gui
    systemctl start tisbackup_gui
    systemctl enable tisbackup_huey
    systemctl start tisbackup_huey
```

You can then see the result in your browser: ```http://backup-server-name:8080```
