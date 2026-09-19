export PATH="$HOME/.npm-global/bin:$PATH"
export PATH="$PATH:$HOME/.spicetify"
export LANG=en_US.UTF-8
export EDITOR=nano

autoload -Uz compinit
compinit

HISTSIZE=10000
SAVEHIST=10000
setopt SHARE_HISTORY
setopt HIST_IGNORE_ALL_DUPS
setopt AUTO_CD
setopt EXTENDED_GLOB
setopt INTERACTIVE_COMMENTS

PROMPT='%n@%m %~ %# '

alias ll='ls -lah'
alias la='ls -A'
alias c='clear'
alias cmatrix='cmatrix -C white'
alias tty-clock='tty-clock -C 7 -c'
