GOPATH=$(shell pwd)/go
build:
	env GOPATH=$(GOPATH) go get -v github.com/deliveroo/uncoordinated
	env GOPATH=$(GOPATH) go build -v github.com/deliveroo/uncoordinated

