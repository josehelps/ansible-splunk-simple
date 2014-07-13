#my stuff
alias elastic='ssh drac0@elastic.josehelps.com'
alias raspberry='ssh pi@10.0.0.200'
alias homerouter='ssh -p 9999 root@home.josehelps.com'
alias cymru='sh cymru'
alias flytrap='ssh drac0@199.180.255.97'
alias indicatorintel='ssh -i /home/drac0/Dropbox/PASSWORDS/indicatorintel.pem ubuntu@107.22.220.213'
#alias flyanalysis='ssh vz@208.110.69.194'
alias flyanalysis='ssh root@67.202.108.205'
alias flysensor='ssh drac0@199.180.255.97'
alias homeserver='ssh -p 2222 divious1@home.josehelps.com'
alias homservergui='ssh -p 2222 -l divious1 -X -v home.josehelps.com'
alias nova='ssh jh1798@scis.nova.edu'
alias activate='. venv/bin/activate'
#actiavate ansible
alias activate_ansible='source /opt/ansible/hacking/env-setup'

## Colorize the ls output ##
alias ls='ls --color=auto'

## Use a long listing format ##
alias ll='ls -la'

## Show hidden files ##
alias l.='ls -d .* --color=auto'

## get rid of command not found ##
alias cd..='cd ..'

## a quick way to get out of current directory ##
alias ..='cd ..'
alias ...='cd ../../../'
alias ....='cd ../../../../'
alias .....='cd ../../../../'
alias .4='cd ../../../../'
alias .5='cd ../../../../..'

## Colorize the grep command output for ease of use (good for log files)##
alias grep='grep --color=auto'
alias egrep='egrep --color=auto'
alias fgrep='fgrep --color=auto'

alias path='echo -e ${PATH//:/\\n}'
alias now='date +"%T'
alias nowtime=now
alias nowdate='date +"%d-%m-%Y"'

alias ports='netstat -tulanp'

## shortcut  for iptables and pass it via sudo#
alias ipt='sudo /sbin/iptables'

# display all rules #
alias iptlist='sudo /sbin/iptables -L -n -v --line-numbers'
alias iptlistin='sudo /sbin/iptables -L INPUT -n -v --line-numbers'
alias iptlistout='sudo /sbin/iptables -L OUTPUT -n -v --line-numbers'
alias iptlistfw='sudo /sbin/iptables -L FORWARD -n -v --line-numbers'
alias firewall=iptlist

# do not delete / or prompt if deleting more than 3 files at a time #
#alias rm='rm -I --preserve-root'

# confirmation #
#alias mv='mv -i'
#alias cp='cp -i'
#alias ln='ln -i'

# Parenting changing perms on / #
#alias chown='chown --preserve-root'
#alias chmod='chmod --preserve-root'
#alias chgrp='chgrp --preserve-root'

# reboot / halt / poweroff
alias reboot='sudo /sbin/reboot'
alias poweroff='sudo /sbin/poweroff'
alias halt='sudo /sbin/halt'
alias shutdown='sudo /sbin/shutdown'

## pass options to free ##
alias meminfo='free -m -l -t'

## get top process eating memory
alias psmem='ps auxf | sort -nr -k 4'
alias psmem10='ps auxf | sort -nr -k 4 | head -10'

## get top process eating cpu ##
alias pscpu='ps auxf | sort -nr -k 3'
alias pscpu10='ps auxf | sort -nr -k 3 | head -10'

## Get server cpu info ##
alias cpuinfo='lscpu'

## this one saved by butt so many times ##
alias wget='wget -c'

## set some other defaults ##
alias df='df -H'
alias du='du -ch'

#add path
export PATH=/opt/local/bin:/opt/local/sbin:$PATH
export PS1="\[\e[01;36m\]\u\[\e[0m\]\[\e[01;37m\]@\[\e[0m\]\[\e[01;32m\]\h\[\e[0m\]\[\e[01;37m\]:\[\e[0m\]\[\e[01;32m\]\w\[\e[0m\]\[\e[01;37m\]\\$\[\e[0m\]"
