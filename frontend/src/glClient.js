import { createClient } from 'genlayer-js'
import { studionet, testnetBradbury } from 'genlayer-js/chains'
import { getNetwork } from './api'

const CONTRACTS = {
  studionet: '0x5b1C73fb7F1df7081126bF473eB40FfE77F05DFb',
  bradbury: '0x6E7694c3ffbB4b109b2A37D009cE29425039E9da',
}

const CHAINS = {
  studionet,
  bradbury: testnetBradbury,
}

const CHAIN_NAMES = {
  studionet: 'studionet',
  bradbury: 'testnetBradbury',
}

export function getContractAddress(net) {
  return CONTRACTS[net || getNetwork()]
}

export function getChain(net) {
  return CHAINS[net || getNetwork()] || studionet
}

export function createReadClient(net) {
  return createClient({ chain: getChain(net) })
}

export function createWriteClient(walletAddress, provider) {
  const net = getNetwork()
  return createClient({
    chain: getChain(net),
    account: walletAddress,
    provider: provider || window.ethereum,
  })
}

export function getChainName(net) {
  return CHAIN_NAMES[net || getNetwork()] || 'studionet'
}
