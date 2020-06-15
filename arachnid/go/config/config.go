package config

import (
	"errors"
	"flag"
	"fmt"
)

type CmdConfig struct {
	ParasTableId string
}

func (c *CmdConfig) ReadCmdParameter() error {
	flag.StringVar(&(c.ParasTableId), "paras", "paras_table", "爬虫参数表名")

	flag.Parse()
	if flag.NFlag() < 1 {
		fmt.Printf("Cmd parameter not enough. now:[%d]\n", flag.NFlag())
		flag.Usage()
		return errors.New("error: not enough cmd parameter")
	}

	return nil
}
