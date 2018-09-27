package main

import (
	"fmt"
	"math/rand"
	"net/http"
	"time"

	"github.com/elazarl/goproxy"
	"github.com/prep/average"
	log "github.com/sirupsen/logrus"
)

type perHostStats struct {
	successes *average.SlidingWindow
	failures  *average.SlidingWindow
}

type circuitBreaker struct {
	hostStats map[string]*perHostStats
	window    time.Duration
}

func newCircuitBreaker(window time.Duration) *circuitBreaker {
	return &circuitBreaker{
		hostStats: make(map[string]*perHostStats),
		window:    window,
	}
}

func (c *circuitBreaker) onRequest(r *http.Request, _ *goproxy.ProxyCtx) (*http.Request, *http.Response) {
	if c.allow(r.Host) {
		return r, nil
	}
	return r, goproxy.NewResponse(r, goproxy.ContentTypeText, http.StatusTooManyRequests, "circuit broken")
}

func (c *circuitBreaker) allow(host string) bool {
	stats, ok := c.hostStats[host]
	if !ok {
		c.hostStats[host] = &perHostStats{
			successes: average.MustNew(c.window, time.Minute),
			failures:  average.MustNew(c.window, time.Minute),
		}
		return true // No stats found for host, assuming OK.
	}
	_, successes := stats.successes.Total(c.window)
	_, failures := stats.failures.Total(c.window)
	successRate := float64(successes) / float64(successes+failures)
	// Allow request to go through if the success rate is larger than a
	// random number in range [0.0,1.0).
	return successRate > rand.Float64()
}

func (c *circuitBreaker) onResponse(r *http.Response, ctx *goproxy.ProxyCtx) *http.Response {
	fmt.Println(r)
	stats, ok := c.hostStats[ctx.Req.Host]
	if !ok {
		return r
	}
	if r.StatusCode >= 500 {
		stats.failures.Add(1)
	} else {
		stats.successes.Add(1)
	}
	return r
}

func main() {
	breaker := newCircuitBreaker(5 * time.Minute)

	// Set up and start proxy.
	proxy := goproxy.NewProxyHttpServer()
	proxy.OnRequest().DoFunc(breaker.onRequest)
	proxy.OnResponse().DoFunc(breaker.onResponse)
	log.Fatal(http.ListenAndServe(":8000", proxy))
}
